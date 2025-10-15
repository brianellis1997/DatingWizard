"""
Instagram Profile Scraper - Scrapes Instagram profiles and posts
Uses web scraping with proper rate limiting and ethical practices
"""

import re
import json
import time
import random
import requests
from typing import Dict, List, Optional, Iterator
from urllib.parse import quote_plus, urljoin
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from loguru import logger

from .base_scraper import ProfileScraper, ProfileData, ScrapingResult, SourceType


class InstagramScraper(ProfileScraper):
    """Instagram profile scraper using web scraping techniques"""
    
    def __init__(self, use_selenium: bool = True, headless: bool = True, **kwargs):
        super().__init__(rate_limit_delay=2.0, max_retries=2, **kwargs)
        self.use_selenium = use_selenium
        self.headless = headless
        self.driver = None
        self.session = requests.Session()
        
        # Setup session headers to avoid detection
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        if self.use_selenium:
            self._setup_selenium()
    
    def get_source_type(self) -> SourceType:
        return SourceType.INSTAGRAM
    
    def _setup_selenium(self):
        """Setup undetected-chromedriver for stealth Instagram scraping"""
        try:
            options = uc.ChromeOptions()

            # Chromium binary location in Docker
            options.binary_location = "/usr/bin/chromium"

            # Additional stealth arguments
            options.add_argument("--disable-notifications")
            options.add_argument("--disable-popup-blocking")
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')

            # Window size to avoid mobile layout
            options.add_argument('--window-size=1920,1080')

            if self.headless:
                options.add_argument('--headless=new')

            # Use undetected-chromedriver with custom chromedriver path
            self.driver = uc.Chrome(
                options=options,
                driver_executable_path='/usr/bin/chromedriver',
                version_main=None,  # Skip version detection
                use_subprocess=True
            )

            # Random initial delay to appear more human
            time.sleep(random.uniform(1, 3))

            logger.info("Undetected-chromedriver initialized for Instagram scraping")

        except Exception as e:
            logger.warning(f"Failed to setup undetected-chromedriver: {e}. Falling back to requests only.")
            self.use_selenium = False
    
    def search_profiles(self, query: str, limit: int = 50, **kwargs) -> ScrapingResult:
        """Search Instagram for profiles matching query"""
        start_time = time.time()
        result = ScrapingResult()
        result.total_found = limit
        
        try:
            # Instagram search methods
            search_methods = [
                self._search_by_hashtag,
                self._search_by_location,
                self._search_by_username
            ]
            
            profiles_found = []
            
            for search_method in search_methods:
                try:
                    method_profiles = search_method(query, limit // len(search_methods))
                    profiles_found.extend(method_profiles)
                    
                    if len(profiles_found) >= limit:
                        break
                        
                except Exception as e:
                    logger.warning(f"Search method {search_method.__name__} failed: {e}")
                    result.add_error(f"{search_method.__name__}: {str(e)}")
            
            # Remove duplicates
            unique_profiles = self._deduplicate_by_username(profiles_found)
            
            # Limit results
            final_profiles = unique_profiles[:limit]
            
            for profile in final_profiles:
                if self.validate_profile(profile):
                    result.add_profile(profile)
                else:
                    result.skip_profile("Invalid profile data")
            
            result.execution_time = time.time() - start_time
            logger.info(f"Instagram search completed: {result.successful} profiles found")
            
        except Exception as e:
            logger.error(f"Instagram search failed: {e}")
            result.add_error(str(e))
            result.execution_time = time.time() - start_time
        
        return result
    
    def _enhance_query_for_people(self, query: str) -> List[str]:
        """Enhance query to better find people/profiles"""
        enhanced_queries = []
        
        # Basic query
        enhanced_queries.append(query)
        
        # Add people-focused terms
        enhanced_queries.append(f"{query} person")
        enhanced_queries.append(f"{query} profile")
        
        return enhanced_queries[:3]  # Limit to avoid too many requests
    
    def _search_by_hashtag(self, hashtag: str, limit: int = 20) -> List[ProfileData]:
        """Search profiles by hashtag"""
        profiles = []
        
        if not hashtag.startswith('#'):
            hashtag = f"#{hashtag}"
        
        hashtag_clean = hashtag.replace('#', '').replace(' ', '')
        
        if self.use_selenium and self.driver:
            profiles.extend(self._selenium_hashtag_search(hashtag_clean, limit))
        else:
            profiles.extend(self._requests_hashtag_search(hashtag_clean, limit))
        
        return profiles
    
    def _search_by_location(self, location: str, limit: int = 20) -> List[ProfileData]:
        """Search profiles by location (limited without Instagram API)"""
        # This is very limited without official API
        # We can try to find location-based hashtags
        location_hashtags = [
            f"{location.lower().replace(' ', '')}",
            f"{location.lower().replace(' ', '')}life",
            f"visit{location.lower().replace(' ', '')}",
            f"{location.lower().replace(' ', '')}city"
        ]
        
        profiles = []
        for hashtag in location_hashtags[:2]:  # Limit to avoid too many requests
            try:
                hashtag_profiles = self._search_by_hashtag(hashtag, limit // 2)
                profiles.extend(hashtag_profiles)
            except Exception as e:
                logger.warning(f"Location hashtag search failed for {hashtag}: {e}")
                
        return profiles[:limit]
    
    def _search_by_username(self, username: str, limit: int = 10) -> List[ProfileData]:
        """Search for specific usernames or similar usernames"""
        profiles = []
        
        # Try exact username first
        try:
            profile = self.get_profile_by_id(username)
            if profile:
                profiles.append(profile)
        except Exception as e:
            logger.debug(f"Exact username search failed: {e}")
        
        # Try common variations if we didn't find the exact match
        if not profiles and len(username) > 3:
            variations = [
                f"{username}_official",
                f"real_{username}",
                f"{username}1",
                f"{username}_",
                f"_{username}"
            ]
            
            for variation in variations[:3]:  # Limit variations
                try:
                    profile = self.get_profile_by_id(variation)
                    if profile:
                        profiles.append(profile)
                        break
                except Exception as e:
                    logger.debug(f"Username variation {variation} failed: {e}")
                    
        return profiles
    
    def _selenium_hashtag_search(self, hashtag: str, limit: int = 20) -> List[ProfileData]:
        """Use Selenium to search hashtags"""
        profiles = []
        
        try:
            url = f"https://www.instagram.com/explore/tags/{hashtag}/"
            self.driver.get(url)
            
            # Wait for posts to load
            time.sleep(3)
            
            # Scroll to load more posts
            for _ in range(3):  # Limit scrolling
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
            
            # Find post links
            post_links = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="/p/"]')
            
            processed_users = set()
            
            for link in post_links[:limit * 2]:  # Get more links than needed
                try:
                    post_url = link.get_attribute('href')
                    if post_url:
                        # Extract username from post
                        username = self._extract_username_from_post_url(post_url)
                        if username and username not in processed_users:
                            processed_users.add(username)
                            
                            # Get profile data
                            profile = self._get_profile_data_selenium(username)
                            if profile:
                                profiles.append(profile)
                                
                                if len(profiles) >= limit:
                                    break
                    
                    self.enforce_rate_limit()
                    
                except Exception as e:
                    logger.debug(f"Error processing post link: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Selenium hashtag search failed: {e}")
        
        return profiles
    
    def _requests_hashtag_search(self, hashtag: str, limit: int = 20) -> List[ProfileData]:
        """Use requests to search hashtags (limited functionality)"""
        profiles = []
        
        try:
            url = f"https://www.instagram.com/explore/tags/{hashtag}/"
            self.enforce_rate_limit()
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # Try to extract data from page source (very limited)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for JSON data in script tags
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                try:
                    data = json.loads(script.text)
                    # Extract what we can from structured data
                    # This is very limited compared to the full API
                    
                except json.JSONDecodeError:
                    continue
                    
        except Exception as e:
            logger.error(f"Requests hashtag search failed: {e}")
        
        return profiles
    
    def get_profile_by_id(self, username: str) -> Optional[ProfileData]:
        """Get specific Instagram profile by username"""
        try:
            if self.use_selenium and self.driver:
                return self._get_profile_data_selenium(username)
            else:
                return self._get_profile_data_requests(username)
        except Exception as e:
            logger.error(f"Error getting Instagram profile {username}: {e}")
            return None
    
    def _get_profile_data_selenium(self, username: str) -> Optional[ProfileData]:
        """Get profile data using Selenium with human-like behavior"""
        try:
            url = f"https://www.instagram.com/{username}/"

            # Random delay before navigation (2-5 seconds)
            time.sleep(random.uniform(2, 5))

            self.driver.get(url)

            # Random delay after page load (1-3 seconds)
            time.sleep(random.uniform(1, 3))

            # Wait for profile to load with increased timeout
            wait = WebDriverWait(self.driver, 15)

            try:
                # Check if profile exists
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'main')))
            except TimeoutException:
                # Save debug screenshot to see what Instagram is showing
                debug_screenshot = f"uploads/screenshots/instagram/DEBUG_{username}_{int(time.time())}.png"
                self.driver.save_screenshot(debug_screenshot)
                logger.warning(f"Profile {username} may not exist or failed to load. Debug screenshot: {debug_screenshot}")
                return None
            
            # Extract profile data
            profile_data = ProfileData(
                source_id=username,
                source_type=SourceType.INSTAGRAM,
                url=url,
                name=username  # Will try to get real name below
            )
            
            try:
                # Get real name
                name_element = self.driver.find_element(By.CSS_SELECTOR, 'h1')
                if name_element:
                    profile_data.name = name_element.text
            except NoSuchElementException:
                pass
            
            try:
                # Get bio
                bio_elements = self.driver.find_elements(By.CSS_SELECTOR, 'div[data-testid="user-description"]')
                if bio_elements:
                    profile_data.bio = bio_elements[0].text
            except NoSuchElementException:
                pass
            
            try:
                # Get follower count
                stats_elements = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="/followers/"] span')
                if stats_elements:
                    followers_text = stats_elements[0].text
                    profile_data.followers = self._parse_instagram_number(followers_text)
            except (NoSuchElementException, IndexError):
                pass
            
            try:
                # Get profile images
                img_elements = self.driver.find_elements(By.CSS_SELECTOR, 'img[alt*="profile picture"], img[src*="profile"]')
                for img in img_elements:
                    src = img.get_attribute('src')
                    if src and 'profile' in src.lower():
                        profile_data.profile_images.append(src)
                        break
                        
                # Get post images (first few)
                post_images = self.driver.find_elements(By.CSS_SELECTOR, 'article img')
                for img in post_images[:6]:  # Limit to first 6 posts
                    src = img.get_attribute('src')
                    if src:
                        profile_data.profile_images.append(src)
                        
                profile_data.image_count = len(profile_data.profile_images)
                
            except NoSuchElementException:
                pass
            
            # Mark as complete if we got essential data
            if profile_data.name and (profile_data.bio or profile_data.profile_images):
                profile_data.is_complete = True
                profile_data.confidence_score = 0.8
            else:
                profile_data.confidence_score = 0.4
            
            self.enforce_rate_limit()
            return profile_data
            
        except Exception as e:
            logger.error(f"Error getting profile data for {username}: {e}")
            return None
    
    def _get_profile_data_requests(self, username: str) -> Optional[ProfileData]:
        """Get profile data using requests (very limited)"""
        try:
            url = f"https://www.instagram.com/{username}/"
            self.enforce_rate_limit()
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Basic profile data
            profile_data = ProfileData(
                source_id=username,
                source_type=SourceType.INSTAGRAM,
                url=url,
                name=username
            )
            
            # Try to extract from meta tags
            og_title = soup.find('meta', property='og:title')
            if og_title:
                profile_data.name = og_title.get('content', username)
            
            og_description = soup.find('meta', property='og:description')
            if og_description:
                profile_data.bio = og_description.get('content', '')
            
            og_image = soup.find('meta', property='og:image')
            if og_image:
                profile_data.profile_images.append(og_image.get('content'))
                profile_data.image_count = 1
            
            profile_data.confidence_score = 0.5  # Limited data quality
            return profile_data
            
        except Exception as e:
            logger.error(f"Error getting profile data for {username}: {e}")
            return None
    
    def get_profile_images(self, profile: ProfileData) -> List[str]:
        """Get all image URLs for a profile"""
        return profile.profile_images
    
    def _extract_username_from_post_url(self, post_url: str) -> Optional[str]:
        """Extract username from Instagram post URL"""
        # Instagram post URLs are like: https://www.instagram.com/p/POST_ID/
        # We need to navigate to the post to find the username
        # This is a simplified approach
        if '/p/' in post_url:
            try:
                if self.use_selenium and self.driver:
                    self.driver.get(post_url)
                    time.sleep(2)
                    
                    # Look for username link
                    username_links = self.driver.find_elements(By.CSS_SELECTOR, 'a[href^="/"][href$="/"]')
                    for link in username_links:
                        href = link.get_attribute('href')
                        if href and href.count('/') == 4:  # Format: https://instagram.com/username/
                            username = href.split('/')[-2]
                            if username and len(username) > 0:
                                return username
                                
            except Exception as e:
                logger.debug(f"Error extracting username from post URL: {e}")
        
        return None
    
    def _parse_instagram_number(self, text: str) -> Optional[int]:
        """Parse Instagram number format (e.g., '1.2k', '10M')"""
        if not text:
            return None
            
        text = text.lower().replace(',', '')
        
        try:
            if 'k' in text:
                return int(float(text.replace('k', '')) * 1000)
            elif 'm' in text:
                return int(float(text.replace('m', '')) * 1000000)
            else:
                return int(text)
        except ValueError:
            return None
    
    def _deduplicate_by_username(self, profiles: List[ProfileData]) -> List[ProfileData]:
        """Remove duplicate profiles by username"""
        seen_usernames = set()
        unique_profiles = []
        
        for profile in profiles:
            username = profile.source_id
            if username not in seen_usernames:
                seen_usernames.add(username)
                unique_profiles.append(profile)
        
        return unique_profiles
    
    def normalize_profile_data(self, raw_data: Dict) -> ProfileData:
        """Convert Instagram-specific data to standardized ProfileData"""
        return ProfileData(
            source_id=raw_data.get('username', ''),
            source_type=SourceType.INSTAGRAM,
            url=f"https://www.instagram.com/{raw_data.get('username', '')}/",
            name=raw_data.get('full_name') or raw_data.get('username', ''),
            bio=raw_data.get('biography', ''),
            followers=raw_data.get('follower_count'),
            following=raw_data.get('following_count'),
            verified=raw_data.get('is_verified', False),
            profile_images=[raw_data.get('profile_pic_url')] if raw_data.get('profile_pic_url') else [],
            extra_data={
                'is_private': raw_data.get('is_private', False),
                'post_count': raw_data.get('media_count', 0),
                'external_url': raw_data.get('external_url')
            }
        )
    
    def close(self):
        """Clean up resources"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Instagram scraper driver closed")
            except Exception as e:
                logger.warning(f"Error closing Instagram scraper driver: {e}")
    
    def __del__(self):
        """Ensure cleanup on deletion"""
        self.close()