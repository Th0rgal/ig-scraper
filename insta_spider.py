from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import json
import time
import os
import argparse
from datetime import datetime
import random
import zipfile
import tempfile
from urllib.parse import urlparse, unquote

# Use Selenium Manager (built-in) to locate the correct ChromeDriver for the host OS
service = Service()


def scrape_instagram_profile(
    username, headless=True, timeout=30, debug=False, proxy: str | None = None
):
    """
    Scrape Instagram profile posts and return image sources with captions in JSON format
    """
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,1200")
    options.add_argument("--lang=en-US")

    # Anti-detection tweaks
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--allow-insecure-localhost")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # Realistic desktop user-agent (mobile fallback will use m. domain)
    DESKTOP_USER_AGENTS = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
    ]
    ua = random.choice(DESKTOP_USER_AGENTS)
    options.add_argument(f"--user-agent={ua}")

    # Proxy support: if credentials are present, use a temporary extension for auth
    if proxy:
        parsed = urlparse(proxy)
        scheme = (parsed.scheme or "http").lower()
        host = parsed.hostname
        port = parsed.port
        user = unquote(parsed.username) if parsed.username else None
        pwd = unquote(parsed.password) if parsed.password else None

        if user and pwd:
            try:
                ext_path = _build_proxy_auth_extension(scheme, host, port, user, pwd)
                options.add_extension(ext_path)
                if debug:
                    print(f"[DEBUG] Using proxy (extension): {scheme}://{host}:{port}")
            except Exception as e:
                print(f"[DEBUG] Failed to attach proxy auth extension: {e}")
                options.add_argument(f"--proxy-server={scheme}://{host}:{port}")
        else:
            # No auth in URL; use native proxy flag
            options.add_argument(f"--proxy-server={scheme}://{host}:{port}")

        # Note: If extension is used, headless may be unreliable for auth prompts.
        # If you see issues, run with --no-headless.
        if debug and (user and pwd):
            print(
                "[DEBUG] Tip: If login prompts appear, use --no-headless with proxy auth extension."
            )

    if debug:
        # Increase Chrome logging and enable browser logs
        options.add_argument("--enable-logging=stderr")
        options.add_argument("--v=1")
        options.set_capability("goog:loggingPrefs", {"browser": "ALL"})

    driver = webdriver.Chrome(service=service, options=options)

    try:
        # Pretend we came from Google to avoid login wall
        try:
            driver.execute_cdp_cmd("Network.enable", {})
            driver.execute_cdp_cmd(
                "Network.setExtraHTTPHeaders",
                {"headers": {"Referer": "https://www.google.com/"}},
            )
        except Exception:
            pass

        driver.get(f"https://www.instagram.com/{username}/")
        wait = WebDriverWait(driver, timeout)

        if debug:
            print("[DEBUG] Current URL:", driver.current_url)
            print("[DEBUG] Page title:", driver.title)
            try:
                print(
                    "[DEBUG] Capabilities browser/version:",
                    driver.capabilities.get("browserName"),
                    driver.capabilities.get("browserVersion"),
                )
            except Exception:
                pass

        # Hide webdriver flag
        try:
            driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
        except Exception:
            pass

        # Wait for the article element containing posts
        article = None
        try:
            article = wait.until(
                EC.presence_of_element_located((By.TAG_NAME, "article"))
            )
        except TimeoutException:
            # If redirected to login, try mobile site
            if "/accounts/login" in driver.current_url or "Log in" in driver.title:
                if debug:
                    print(
                        "[DEBUG] Redirected to login on desktop. Trying mobile site..."
                    )
                try:
                    driver.get(f"https://m.instagram.com/{username}/")
                    article = WebDriverWait(driver, timeout).until(
                        EC.presence_of_element_located((By.TAG_NAME, "article"))
                    )
                except TimeoutException:
                    if debug:
                        print(
                            "[DEBUG] Mobile site did not expose <article>. Will broad-scan anchors."
                        )
        time.sleep(3)  # Allow content to load

        # Keep clicking "Show more posts" button until it's no longer available
        while True:
            try:
                # Find the actual button element (not the span inside it)
                show_more_button = driver.find_element(
                    By.XPATH,
                    "//button[contains(@class, 'x1lugfcp') and .//span[contains(text(), 'Show more posts')]]",
                )
                button_text = show_more_button.text
                print(f"Found button with text: '{button_text}' - clicking it...")

                # Use JavaScript click to avoid interception issues (no scrolling)
                driver.execute_script("arguments[0].click();", show_more_button)

                # Wait a couple of seconds for new content to load
                time.sleep(3)

            except NoSuchElementException:
                print(
                    "Show more posts button not found - all posts should be loaded now"
                )
                break
            except Exception as e:
                print(f"Error clicking button: {str(e)}")
                break

        # Now collect all the posts after loading everything
        posts = []
        post_links = []
        if article:
            post_links = article.find_elements(By.TAG_NAME, "a")
        else:
            # Fallback: broad scan for anchors
            try:
                post_links = driver.find_elements(By.TAG_NAME, "a")
            except Exception:
                post_links = []

        for link in post_links:
            try:
                # Find image in the post
                img_element = link.find_element(By.TAG_NAME, "img")
                img_src = img_element.get_attribute("src")

                if not img_src:
                    continue

                # Try to find caption - Instagram captions can be in various locations
                caption = ""
                try:
                    post_wrapper = link.find_element(By.XPATH, "./..")

                    h2_span = post_wrapper.find_element(By.XPATH, ".//h2/span")
                    caption = h2_span.get_attribute("innerHTML")
                except NoSuchElementException:
                    pass

                if img_src:
                    posts.append({"img_src": img_src, "img_caption": caption})

            except NoSuchElementException:
                continue

        # Remove duplicates based on img_src
        unique_posts = []
        seen_srcs = set()
        for post in posts:
            if post["img_src"] not in seen_srcs:
                unique_posts.append(post)
                seen_srcs.add(post["img_src"])

        result = {
            "username": username,
            "total_posts": len(unique_posts),
            "posts": unique_posts,
        }

        return result

    except TimeoutException:
        print(f"Timed out after {timeout}s — Profile not found or failed to load")
        if debug:
            _dump_debug_artifacts(driver, prefix=f"timeout_{username}")
        return {"username": username, "total_posts": 0, "posts": []}
    except Exception as e:
        print(f"Error scraping profile: {str(e)}")
        if debug:
            _dump_debug_artifacts(driver, prefix=f"error_{username}")
        return {"username": username, "total_posts": 0, "posts": []}
    finally:
        driver.quit()


def _dump_debug_artifacts(driver, prefix: str) -> None:
    """Write debug artifacts (HTML, screenshot, console logs) to ./debug directory."""
    try:
        os.makedirs("debug", exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = os.path.join("debug", f"{prefix}_{ts}")
        # HTML dump
        try:
            with open(base + ".html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print(f"[DEBUG] Saved HTML to {base}.html")
        except Exception as e:
            print(f"[DEBUG] Failed to save HTML: {e}")
        # Screenshot (may fail in headless old mode)
        try:
            driver.save_screenshot(base + ".png")
            print(f"[DEBUG] Saved screenshot to {base}.png")
        except Exception as e:
            print(f"[DEBUG] Failed to save screenshot: {e}")
        # Console logs
        try:
            logs = driver.get_log("browser") or []
            with open(base + ".log", "w", encoding="utf-8") as f:
                for entry in logs:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            print(f"[DEBUG] Saved console log to {base}.log")
        except Exception as e:
            print(f"[DEBUG] Failed to collect console logs: {e}")
    except Exception as e:
        print(f"[DEBUG] Unexpected error while writing debug artifacts: {e}")


def _build_proxy_auth_extension(
    scheme: str, host: str, port: int, username: str, password: str
) -> str:
    """Create a temporary Chrome extension that sets a fixed proxy and handles auth.

    Returns the path to the created .zip file. Works for HTTP and SOCKS5 by setting
    the scheme in chrome.proxy rules accordingly.
    """
    # Chrome extension manifest (v2 for broad compatibility)
    manifest = {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking",
        ],
        "background": {"scripts": ["background.js"]},
        "minimum_chrome_version": "22.0.0",
    }

    scheme_for_ext = "socks5" if scheme.startswith("socks") else "http"
    background_js = f"""
var config = {{
  mode: "fixed_servers",
  rules: {{
    singleProxy: {{
      scheme: "{scheme_for_ext}",
      host: "{host}",
      port: parseInt({port})
    }},
    bypassList: ["localhost"]
  }}
}};

chrome.proxy.settings.set({{value: config, scope: "regular"}}, function() {{}});

function callbackFn(details) {{
  return {{ authCredentials: {{ username: "{username}", password: "{password}" }} }};
}}

chrome.webRequest.onAuthRequired.addListener(
  callbackFn,
  {{ urls: ["<all_urls>"] }},
  ['blocking']
);
"""

    tmp_dir = tempfile.mkdtemp(prefix="proxy_ext_")
    ext_zip_path = os.path.join(tmp_dir, "proxy_auth_plugin.zip")
    manifest_path = os.path.join(tmp_dir, "manifest.json")
    background_path = os.path.join(tmp_dir, "background.js")

    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(manifest))
    with open(background_path, "w", encoding="utf-8") as f:
        f.write(background_js)

    with zipfile.ZipFile(ext_zip_path, "w") as zp:
        zp.write(manifest_path, arcname="manifest.json")
        zp.write(background_path, arcname="background.js")

    return ext_zip_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Instagram profile scraper")
    parser.add_argument("--username", "-u", help="Instagram username")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout seconds")
    parser.add_argument(
        "--debug", action="store_true", help="Enable verbose debug and dumps"
    )
    parser.add_argument(
        "--proxy",
        help="HTTP/HTTPS proxy, e.g., http://user:pass@host:port or http://host:port",
    )
    headless_group = parser.add_mutually_exclusive_group()
    headless_group.add_argument(
        "--headless",
        dest="headless",
        action="store_true",
        help="Run headless (default)",
    )
    headless_group.add_argument(
        "--no-headless",
        dest="headless",
        action="store_false",
        help="Run with browser UI",
    )
    parser.set_defaults(headless=True)
    args = parser.parse_args()

    username = args.username or input("Enter Instagram username: ").strip()
    if not username:
        print("Username cannot be empty!")
        exit(1)

    data = scrape_instagram_profile(
        username,
        headless=args.headless,
        timeout=args.timeout,
        debug=args.debug,
        proxy=args.proxy,
    )
    print(json.dumps(data, indent=2, ensure_ascii=False))
