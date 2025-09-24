from __future__ import annotations

import random
from urllib.parse import urlparse, unquote
import sys

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from utils.debug import dump_debug_artifacts
from utils.proxy import build_proxy_auth_extension

try:
    from seleniumwire import webdriver as wire_webdriver

    _SW_IMPORT_ERR = None
except Exception as e:
    wire_webdriver = None
    _SW_IMPORT_ERR = repr(e)


def create_driver(headless: bool, debug: bool, proxy: str | None) -> webdriver.Chrome:
    service = Service()
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,1200")
    options.add_argument("--lang=en-US")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--allow-insecure-localhost")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    DESKTOP_USER_AGENTS = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
    ]
    ua = random.choice(DESKTOP_USER_AGENTS)
    options.add_argument(f"--user-agent={ua}")

    if debug:
        options.add_argument("--enable-logging=stderr")
        options.add_argument("--v=1")
        options.set_capability("goog:loggingPrefs", {"browser": "ALL"})

    if proxy:
        parsed = urlparse(proxy)
        scheme = (parsed.scheme or "http").lower()
        host = parsed.hostname
        port = parsed.port
        user = unquote(parsed.username) if parsed.username else None
        pwd = unquote(parsed.password) if parsed.password else None

        if wire_webdriver is not None:
            # Build full proxy URLs with credentials embedded (works reliably with selenium-wire)
            if user and pwd:
                auth_part = f"{user}:{pwd}@"
            else:
                auth_part = ""

            # Normalize schemes: for HTTP proxies, use http:// for both http and https targets
            if scheme in ("http", "https"):
                http_proxy_url = f"http://{auth_part}{host}:{port}"
                https_proxy_url = f"http://{auth_part}{host}:{port}"
            else:
                # socks5 or socks5h
                socks_scheme = "socks5h" if scheme.startswith("socks5h") else "socks5"
                http_proxy_url = f"{socks_scheme}://{auth_part}{host}:{port}"
                https_proxy_url = http_proxy_url

            seleniumwire_options = {
                "proxy": {
                    "http": http_proxy_url,
                    "https": https_proxy_url,
                }
            }

            driver = wire_webdriver.Chrome(
                service=service,
                options=options,
                seleniumwire_options=seleniumwire_options,
            )
            if debug:
                print(
                    f"[DEBUG] Using selenium-wire proxy: {http_proxy_url} (auth={'yes' if user and pwd else 'no'})"
                )
        else:
            # Native Chrome fallback: flags or auth extension
            if user and pwd:
                try:
                    ext_path = build_proxy_auth_extension(scheme, host, port, user, pwd)
                    options.add_extension(ext_path)
                    if debug:
                        print(
                            f"[DEBUG] Using native Chrome with proxy auth extension: {scheme}://{host}:{port}"
                        )
                except Exception as e:
                    if debug:
                        print(f"[DEBUG] Failed to attach proxy auth extension: {e}")
                    options.add_argument(f"--proxy-server={scheme}://{host}:{port}")
                    if debug:
                        print(
                            f"[DEBUG] Falling back to --proxy-server flag: {scheme}://{host}:{port}"
                        )
            else:
                options.add_argument(f"--proxy-server={scheme}://{host}:{port}")
                if debug:
                    print(
                        f"[DEBUG] Using native Chrome with --proxy-server: {scheme}://{host}:{port}"
                    )
            driver = webdriver.Chrome(service=service, options=options)
            if debug:
                msg = f"[DEBUG] selenium-wire not available (py={sys.executable}); native Chrome initialized"
                if _SW_IMPORT_ERR:
                    msg += f" — import error: {_SW_IMPORT_ERR}"
                print(msg)
    else:
        driver = webdriver.Chrome(service=service, options=options)
    try:
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
    except Exception:
        pass
    try:
        driver.execute_cdp_cmd("Network.enable", {})
        driver.execute_cdp_cmd(
            "Network.setExtraHTTPHeaders",
            {"headers": {"Referer": "https://www.google.com/"}},
        )
    except Exception:
        pass
    return driver


def scrape_instagram_profile(
    username: str,
    headless: bool = True,
    timeout: int = 30,
    debug: bool = False,
    proxy: str | None = None,
):
    options_msg = (
        f"headless={headless}, timeout={timeout}, proxy={'yes' if proxy else 'no'}"
    )
    if debug:
        print(f"[DEBUG] scrape options: {options_msg}")

    driver = create_driver(headless=headless, debug=debug, proxy=proxy)
    try:
        if debug:
            try:
                driver.get(
                    "https://ipv4.icanhazip.com/?_=" + str(random.randint(1, 1_000_000))
                )
                WebDriverWait(driver, timeout).until(
                    lambda d: d.execute_script("return document.readyState")
                    == "complete"
                )
                ip_txt = driver.execute_script(
                    "return document.body ? document.body.innerText : '';"
                )
                ip_txt = (ip_txt or "").strip()
                print(
                    f"[DEBUG] Outbound IP as seen by icanhazip: {ip_txt or 'unknown'}"
                )
            except Exception as e:
                print(f"[DEBUG] Failed to probe proxy IP: {e}")
        driver.get(f"https://www.instagram.com/{username}/")
        wait = WebDriverWait(driver, timeout)

        if debug:
            print("[DEBUG] Current URL:", driver.current_url)
            print("[DEBUG] Page title:", driver.title)

        article = None
        try:
            article = wait.until(
                EC.presence_of_element_located((By.TAG_NAME, "article"))
            )
        except TimeoutException:
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

        posts = []
        links = []
        if article:
            links = article.find_elements(By.TAG_NAME, "a")
        else:
            try:
                links = driver.find_elements(By.TAG_NAME, "a")
            except Exception:
                links = []

        for link in links:
            try:
                img = link.find_element(By.TAG_NAME, "img")
                src = img.get_attribute("src")
                if not src:
                    continue
                caption = ""
                try:
                    parent = link.find_element(By.XPATH, "./..")
                    h2_span = parent.find_element(By.XPATH, ".//h2/span")
                    caption = h2_span.get_attribute("innerHTML")
                except NoSuchElementException:
                    pass
                posts.append({"img_src": src, "img_caption": caption})
            except NoSuchElementException:
                continue

        # De-dup by img_src
        seen = set()
        unique_posts = []
        for p in posts:
            s = p.get("img_src")
            if s and s not in seen:
                seen.add(s)
                unique_posts.append(p)

        return {
            "username": username,
            "total_posts": len(unique_posts),
            "posts": unique_posts,
        }
    except TimeoutException:
        if debug:
            dump_debug_artifacts(driver, prefix=f"timeout_{username}")
        return {"username": username, "total_posts": 0, "posts": []}
    except Exception as e:
        print(f"Error scraping profile: {str(e)}")
        if debug:
            dump_debug_artifacts(driver, prefix=f"error_{username}")
        return {"username": username, "total_posts": 0, "posts": []}
    finally:
        driver.quit()
