"""
Tinder Web Controller using Selenium
Handles all interactions with Tinder's web interface
"""

import time
import random
from typing import Dict, List, Optional, Tuple
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from loguru import logger


class TinderController:
    """Controls Tinder Web interactions via Selenium"""
    
    def __init__(self, headless: bool = False):
        self.driver = None
        self.headless = headless
        self.wait = None
        self._setup_driver()
        
    def _setup_driver(self):
        """Initialize Chrome driver with optimal settings"""
        options = webdriver.ChromeOptions()
        
        # Essential options for automation
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("--disable-notifications")
        
        # Performance options
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        if self.headless:
            options.add_argument('--headless')
            
        # User agent to appear more human-like
        options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
        
        # For newer selenium versions
        from selenium.webdriver.chrome.service import Service
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait = WebDriverWait(self.driver, 10)
        
        # Execute script to remove webdriver property
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
    def login(self, email: str = None, password: str = None, use_phone: bool = False):
        """Login to Tinder Web"""
        logger.info("Navigating to Tinder...")
        self.driver.get("https://tinder.com")
        
        time.sleep(5)  # Wait for page load
        
        try:
            # Wait longer for login button
            wait_long = WebDriverWait(self.driver, 30)
            
            # Try to find and click login button
            try:
                login_btn = wait_long.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Log in')]"))
                )
                login_btn.click()
            except:
                # Alternative: look for "Sign in" or other variations
                try:
                    login_btn = self.driver.find_element(By.XPATH, "//a[contains(text(), 'Log in')]")
                    login_btn.click()
                except:
                    logger.info("Could not find login button automatically")
            
            # Manual login
            logger.info("Please complete the login process manually in the browser...")
            logger.info("This includes any popups, permissions, or verification steps")
            input("Press Enter in the terminal AFTER you are fully logged in and can see profiles...")
                
            logger.success("Login successful!")
            return True
            
        except Exception as e:
            logger.warning(f"Login process issue: {e}")
            logger.info("Manual login required...")
            input("Press Enter after manually logging in...")
            return True
            
    def get_current_profile(self) -> Dict:
        """Extract current profile information"""
        profile_data = {
            'name': None,
            'age': None,
            'bio': None,
            'distance': None,
            'images': [],
            'interests': []
        }
        
        try:
            # Wait for profile card to be present
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[class*="recsCard"]'))
            )
            
            # Extract name and age
            try:
                name_age = self.driver.find_element(By.CSS_SELECTOR, '[itemprop="name"]').text
                if name_age:
                    parts = name_age.rsplit(' ', 1)
                    profile_data['name'] = parts[0] if parts else name_age
                    profile_data['age'] = parts[1] if len(parts) > 1 else None
            except NoSuchElementException:
                pass
                
            # Extract bio
            try:
                # Click to expand bio if needed
                expand_btn = self.driver.find_element(By.CSS_SELECTOR, '[class*="ExpandText"]')
                if expand_btn:
                    expand_btn.click()
                    time.sleep(0.5)
            except:
                pass
                
            try:
                bio_element = self.driver.find_element(By.CSS_SELECTOR, '[class*="BreakWord"]')
                profile_data['bio'] = bio_element.text
            except NoSuchElementException:
                pass
                
            # Extract distance
            try:
                distance_element = self.driver.find_element(By.XPATH, "//*[contains(text(), 'miles away')]")
                profile_data['distance'] = distance_element.text
            except NoSuchElementException:
                pass
                
            # Extract images
            try:
                image_elements = self.driver.find_elements(By.CSS_SELECTOR, '[class*="media"] [role="img"]')
                for img in image_elements:
                    style = img.get_attribute('style')
                    if 'background-image' in style:
                        url = style.split('url("')[1].split('")')[0]
                        profile_data['images'].append(url)
            except:
                pass
                
            # Extract interests/passions
            try:
                interest_elements = self.driver.find_elements(By.CSS_SELECTOR, '[class*="Pill"]')
                profile_data['interests'] = [elem.text for elem in interest_elements if elem.text]
            except:
                pass
                
            logger.debug(f"Extracted profile: {profile_data['name']}, {profile_data['age']}")
            return profile_data
            
        except TimeoutException:
            logger.warning("Could not extract profile - no profile card found")
            return profile_data
            
    def swipe_right(self) -> bool:
        """Perform right swipe (like)"""
        try:
            # Method 1: Click Like button
            like_button = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '[aria-label="Like"]'))
            )
            like_button.click()
            logger.info("Swiped right ✓")
            return True
        except:
            try:
                # Method 2: Keyboard shortcut
                actions = ActionChains(self.driver)
                actions.send_keys("➡").perform()
                logger.info("Swiped right via keyboard ✓")
                return True
            except:
                logger.error("Failed to swipe right")
                return False
                
    def swipe_left(self) -> bool:
        """Perform left swipe (pass)"""
        try:
            # Method 1: Click Nope button
            nope_button = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '[aria-label="Nope"]'))
            )
            nope_button.click()
            logger.info("Swiped left ✗")
            return True
        except:
            try:
                # Method 2: Keyboard shortcut
                actions = ActionChains(self.driver)
                actions.send_keys("⬅").perform()
                logger.info("Swiped left via keyboard ✗")
                return True
            except:
                logger.error("Failed to swipe left")
                return False
                
    def super_like(self) -> bool:
        """Perform super like"""
        try:
            super_like_button = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '[aria-label="Super Like"]'))
            )
            super_like_button.click()
            logger.info("Super liked! ⭐")
            return True
        except:
            logger.error("Failed to super like")
            return False
            
    def check_for_match(self) -> bool:
        """Check if a match occurred after swiping"""
        try:
            # Look for match popup
            match_popup = self.driver.find_element(By.XPATH, "//*[contains(text(), 'It\'s a Match')]")
            if match_popup:
                logger.success("It's a match! 🎉")
                return True
        except NoSuchElementException:
            return False
            
    def close_match_popup(self):
        """Close the match popup to continue swiping"""
        try:
            # Try to find and click "Keep Swiping" button
            keep_swiping = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Keep Swiping')]")
            keep_swiping.click()
        except:
            try:
                # Alternative: Press ESC key
                actions = ActionChains(self.driver)
                actions.send_keys("\\x1B").perform()  # ESC key
            except:
                pass
                
    def get_matches(self) -> List[Dict]:
        """Get list of current matches"""
        matches = []
        try:
            # Navigate to matches
            matches_button = self.driver.find_element(By.CSS_SELECTOR, '[href="/app/matches"]')
            matches_button.click()
            time.sleep(2)
            
            # Get all match cards
            match_elements = self.driver.find_elements(By.CSS_SELECTOR, '[class*="matchListItem"]')
            
            for match in match_elements:
                try:
                    name = match.find_element(By.CSS_SELECTOR, '[class*="Ell"]').text
                    avatar = match.find_element(By.CSS_SELECTOR, '[role="img"]')
                    style = avatar.get_attribute('style')
                    image_url = style.split('url("')[1].split('")')[0] if 'url' in style else None
                    
                    matches.append({
                        'name': name,
                        'image': image_url,
                        'element': match
                    })
                except:
                    continue
                    
            logger.info(f"Found {len(matches)} matches")
            return matches
            
        except Exception as e:
            logger.error(f"Failed to get matches: {e}")
            return matches
            
    def open_chat(self, match_name: str) -> bool:
        """Open chat with a specific match"""
        try:
            matches = self.get_matches()
            for match in matches:
                if match['name'].lower() == match_name.lower():
                    match['element'].click()
                    time.sleep(1)
                    logger.info(f"Opened chat with {match_name}")
                    return True
            logger.warning(f"Match {match_name} not found")
            return False
        except Exception as e:
            logger.error(f"Failed to open chat: {e}")
            return False
            
    def send_message(self, message: str) -> bool:
        """Send a message in the current chat"""
        try:
            # Find message input field
            message_input = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[placeholder*="Type a message"]'))
            )
            
            # Type message with human-like delays
            for char in message:
                message_input.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))
                
            # Send message
            send_button = self.driver.find_element(By.CSS_SELECTOR, '[type="submit"]')
            send_button.click()
            
            logger.info(f"Sent message: {message[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
            
    def get_chat_messages(self) -> List[Dict]:
        """Get all messages from current chat"""
        messages = []
        try:
            message_elements = self.driver.find_elements(By.CSS_SELECTOR, '[class*="Message"]')
            
            for msg_elem in message_elements:
                try:
                    # Determine if sent or received
                    classes = msg_elem.get_attribute('class')
                    is_sent = 'text-right' in classes or 'sent' in classes.lower()
                    
                    text = msg_elem.text
                    if text:
                        messages.append({
                            'text': text,
                            'sender': 'user' if is_sent else 'match'
                        })
                except:
                    continue
                    
            return messages
            
        except Exception as e:
            logger.error(f"Failed to get messages: {e}")
            return messages
            
    def take_screenshot(self, filename: str = None) -> str:
        """Take screenshot of current page"""
        if not filename:
            filename = f"screenshot_{int(time.time())}.png"
        filepath = f"data/screenshots/{filename}"
        self.driver.save_screenshot(filepath)
        logger.debug(f"Screenshot saved: {filepath}")
        return filepath
        
    def human_delay(self, min_seconds: float = 1, max_seconds: float = 3):
        """Add human-like delay between actions"""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
        
    def close(self):
        """Close the browser and cleanup"""
        if self.driver:
            self.driver.quit()
            logger.info("Browser closed")