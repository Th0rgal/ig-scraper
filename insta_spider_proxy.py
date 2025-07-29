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

def load_proxies():
    """Load proxies from proxy.txt file (format: ip:port)"""
    proxies = []
    try:
        with open('proxy.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if line and ':' in line:
                    # Default to http proxy since no protocol is specified
                    proxy_address = line
                    proxy_type = 'http'
                    proxies.append({'address': proxy_address, 'type': proxy_type})
    except FileNotFoundError:
        print("proxy.txt file not found")
    return proxies

def test_proxy_in_chrome(proxy_address):
    """Test if a proxy works with Chrome"""
    test_opts = Options()
    test_opts.add_argument('--headless')
    test_opts.add_argument('--disable-gpu')
    test_opts.add_argument('--ignore-certificate-errors')
    test_opts.add_argument('--proxy-server=' + proxy_address)
    test_opts.add_argument('--log-level=3')

    try:
        driver = webdriver.Chrome(service=service, options=test_opts)
        driver.set_page_load_timeout(10)
        driver.get("http://httpbin.org/ip")
        time.sleep(2)
        src = driver.page_source
        driver.quit()
        return "origin" in src
    except:
        return False

def get_working_proxy():
    """Get a working proxy from the list"""
    proxies = load_proxies()
    if not proxies:
        print("No proxies available in proxy.txt")
        return None
    
    # Shuffle proxies to try them in random order
    shuffled_proxies = proxies.copy()
    random.shuffle(shuffled_proxies)
    
    for proxy in shuffled_proxies:
        proxy_address = proxy['address']
        proxy_type = proxy['type']
        
        print(f"🧪 Testing proxy: {proxy_address}")
        
        if test_proxy_in_chrome(proxy_address):
            print(f"✓ Proxy {proxy_address} is working")
            return proxy
        else:
            print(f"✗ Proxy {proxy_address} is not working")
    
    print("❌ No working proxies found")
    return None

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
    Scrape Instagram profile posts and return image sources with captions in JSON format
    """
    # Get a working proxy first
    working_proxy = get_working_proxy()
    if not working_proxy:
        print("Proceeding without proxy...")
        working_proxy = None
    
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
    
    # Configure proxy if available
    if working_proxy:
        proxy_address = working_proxy['address']
        options.add_argument(f'--proxy-server={proxy_address}')
        print(f"🚀 Using proxy: {proxy_address}")
    
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
        if "Log in" in driver.title or "/accounts/login" in driver.current_url:
            print("🔒 Redirected to login. Instagram requires login or blocked the request.")
            return {
                "username": username,
                "total_posts": 0,
                "posts": []
            }
        
        print(f"✓ Successfully loaded profile: {driver.current_url}")
        
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
