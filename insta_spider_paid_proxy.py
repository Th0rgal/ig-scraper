from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import json
import time
import random

service = Service('./chromedriver-win64/chromedriver-win64/chromedriver.exe')

# Paid proxy configuration
STATIC_PROXY = {
    "host": "x.x.x.x",
    "port": "xxxx",
    "username": "***",
    "password": "***"
}

def test_paid_proxy():
    """Test if the paid proxy works with Chrome"""
    test_opts = Options()
    test_opts.add_argument('--headless')
    test_opts.add_argument('--disable-gpu')
    test_opts.add_argument('--ignore-certificate-errors')
    test_opts.add_argument('--log-level=3')
    
    # Configure proxy with authentication
    proxy_string = f"http://{STATIC_PROXY['username']}:{STATIC_PROXY['password']}@{STATIC_PROXY['host']}:{STATIC_PROXY['port']}"
    test_opts.add_argument(f'--proxy-server={proxy_string}')

    try:
        driver = webdriver.Chrome(service=service, options=test_opts)
        driver.set_page_load_timeout(15)
        driver.get("http://httpbin.org/ip")
        time.sleep(3)
        src = driver.page_source
        driver.quit()
        return "origin" in src
    except Exception as e:
        print(f"Proxy test failed: {str(e)}")
        return False

# List of realistic user agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

def scrape_instagram_profile(username, headless=True, timeout=30):
    """
    Scrape Instagram profile posts using paid proxy and return image sources with captions in JSON format
    """
    # Test the paid proxy first
    print(f"🧪 Testing paid proxy: {STATIC_PROXY['host']}:{STATIC_PROXY['port']}")
    
    if not test_paid_proxy():
        print("❌ Paid proxy is not working. Please check your proxy configuration.")
        return {
            "username": username,
            "total_posts": 0,
            "posts": [],
            "error": "Proxy connection failed"
        }
    
    print("✓ Paid proxy is working")
    
    options = Options()
    if headless:
        options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    # Add random user agent
    random_user_agent = random.choice(USER_AGENTS)
    options.add_argument(f'--user-agent={random_user_agent}')
    print(f"Using User Agent: {random_user_agent}")
    
    # Configure paid proxy with authentication
    proxy_string = f"http://{STATIC_PROXY['username']}:{STATIC_PROXY['password']}@{STATIC_PROXY['host']}:{STATIC_PROXY['port']}"
    options.add_argument(f'--proxy-server={proxy_string}')
    print(f"🚀 Using paid proxy: {STATIC_PROXY['host']}:{STATIC_PROXY['port']}")
    
    # Additional options to look more like a real browser
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--allow-insecure-localhost')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(service=service, options=options)
    
    # Execute script to remove webdriver property
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    try:
        driver.get(f'https://www.instagram.com/{username}/')
        wait = WebDriverWait(driver, timeout)
        
        # Check if redirected to login
        time.sleep(2)
        if "Log in" in driver.title or "www.instagram.com" in driver.title or "/accounts/login" in driver.current_url:
            print("🔒 Redirected to login. Instagram requires login or blocked the request.")
            return {
                "username": username,
                "total_posts": 0,
                "posts": []
            }
        
        
        print(f"✓ Successfully loaded profile: {driver.current_url}")
        
        # Debug: Print current page title and HTML source
        print(f"📄 Page Title: {driver.title}")
        print(f"📄 Page URL: {driver.current_url}")
        print(f"🔍 HTML Source (first 500 chars):")
        print("-" * 50)
        print(driver.page_source[:500])
        print("-" * 50)
        
        # Wait for the article element containing posts
        article = wait.until(EC.presence_of_element_located((By.TAG_NAME, 'article')))
        time.sleep(3)  # Allow content to load
        
        posts = []
        post_links = article.find_elements(By.TAG_NAME, 'a')
        
        for link in post_links:
            try:
                # Find image in the post
                img_element = link.find_element(By.TAG_NAME, 'img')
                img_src = img_element.get_attribute('src')
                
                if not img_src:
                    continue
                
                # Try to find caption - Instagram captions can be in various locations
                caption = ""
                try:
                    post_wrapper = link.find_element(By.XPATH, './..')

                    h2_span = post_wrapper.find_element(By.XPATH, './/h2/span')
                    caption = h2_span.get_attribute('innerHTML')
                except NoSuchElementException:
                    pass
                
                if img_src:
                    posts.append({
                        "img_src": img_src,
                        "img_caption": caption
                    })
                    
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
            "posts": unique_posts
        }
        
        return result
        
    except TimeoutException:
        print(f"Timed out after {timeout}s — Profile not found or failed to load")
        return {
            "username": username,
            "total_posts": 0,
            "posts": []
        }
    except Exception as e:
        print(f"Error scraping profile: {str(e)}")
        return {
            "username": username,
            "total_posts": 0,
            "posts": []
        }
    finally:
        driver.quit()

if __name__ == '__main__':
    username = input("Enter Instagram username: ").strip()
    if not username:
        print("Username cannot be empty!")
        exit(1)
    
    data = scrape_instagram_profile(username)
    print(json.dumps(data, indent=2, ensure_ascii=False))