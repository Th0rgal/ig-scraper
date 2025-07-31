from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import json
import time

service = Service('./chromedriver-win64/chromedriver-win64/chromedriver.exe')

def scrape_instagram_profile(username, headless=True, timeout=30):
    """
    Scrape Instagram profile posts and return image sources with captions in JSON format
    """
    options = Options()
    if headless:
        options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        driver.get(f'https://www.instagram.com/{username}/')
        wait = WebDriverWait(driver, timeout)
        
        # Wait for the article element containing posts
        article = wait.until(EC.presence_of_element_located((By.TAG_NAME, 'article')))
        time.sleep(3)  # Allow content to load
        
        # Keep clicking "Show more posts" button until it's no longer available
        while True:
            try:
                # Find the actual button element (not the span inside it)
                show_more_button = driver.find_element(By.XPATH, "//button[contains(@class, 'x1lugfcp') and .//span[contains(text(), 'Show more posts')]]")
                button_text = show_more_button.text
                print(f"Found button with text: '{button_text}' - clicking it...")
                
                # Use JavaScript click to avoid interception issues (no scrolling)
                driver.execute_script("arguments[0].click();", show_more_button)
                
                # Wait a couple of seconds for new content to load
                time.sleep(3)
                
            except NoSuchElementException:
                print("Show more posts button not found - all posts should be loaded now")
                break
            except Exception as e:
                print(f"Error clicking button: {str(e)}")
                break
        
        # Now collect all the posts after loading everything
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
