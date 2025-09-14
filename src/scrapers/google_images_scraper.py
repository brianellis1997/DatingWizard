"""
Google Images Scraper - Searches Google Images for people/portraits
Focuses on finding profile-like images with metadata when possible
"""

import re
import json
import time
import requests
from typing import Dict, List, Optional, Iterator
from urllib.parse import quote_plus, urljoin, urlparse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from loguru import logger
import hashlib
from datetime import datetime

from .base_scraper import ProfileScraper, ProfileData, ScrapingResult, SourceType


class GoogleImagesScraper(ProfileScraper):
    """Google Images scraper for finding people/portrait photos"""
    
    def __init__(self, use_selenium: bool = True, headless: bool = True, **kwargs):
        super().__init__(rate_limit_delay=1.5, max_retries=2, **kwargs)
        self.use_selenium = use_selenium
        self.headless = headless
        self.driver = None
        self.session = requests.Session()
        
        # Setup session headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
        
        if self.use_selenium:
            self._setup_selenium()
    
    def get_source_type(self) -> SourceType:
        return SourceType.GOOGLE_IMAGES
    
    def _setup_selenium(self):
        """Setup Selenium WebDriver"""
        try:
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager
            
            options = webdriver.ChromeOptions()
            
            # Stealth options
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument("--disable-notifications")
            options.add_argument("--disable-popup-blocking")
            
            # Performance options
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-images')  # Don't load images to save bandwidth
            
            if self.headless:
                options.add_argument('--headless')
            
            # User agent
            options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            
            # Remove webdriver property
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("Selenium driver initialized for Google Images scraping")
            
        except Exception as e:
            logger.warning(f"Failed to setup Selenium: {e}. Falling back to requests only.")
            self.use_selenium = False
    
    def search_profiles(self, query: str, limit: int = 50, **kwargs) -> ScrapingResult:
        """Search Google Images for people/portraits matching query"""
        start_time = time.time()
        result = ScrapingResult()
        result.total_found = limit
        
        try:
            # Enhance query for better people/portrait results
            enhanced_queries = self._enhance_query_for_people(query)
            
            all_image_data = []
            
            for enhanced_query in enhanced_queries:
                try:
                    if self.use_selenium and self.driver:
                        images = self._selenium_image_search(enhanced_query, limit // len(enhanced_queries))
                    else:
                        images = self._requests_image_search(enhanced_query, limit // len(enhanced_queries))
                    
                    all_image_data.extend(images)
                    
                    if len(all_image_data) >= limit:
                        break
                        
                except Exception as e:
                    logger.warning(f"Enhanced query '{enhanced_query}' failed: {e}")
                    result.add_error(f"Query '{enhanced_query}': {str(e)}")
            
            # Convert image data to profile data
            profiles = self._convert_images_to_profiles(all_image_data[:limit])
            
            for profile in profiles:
                if self.validate_profile(profile):
                    result.add_profile(profile)
                else:
                    result.skip_profile("Invalid profile data")
            
            result.execution_time = time.time() - start_time
            logger.info(f"Google Images search completed: {result.successful} profiles found")
            
        except Exception as e:
            logger.error(f"Google Images search failed: {e}")
            result.add_error(str(e))
            result.execution_time = time.time() - start_time
        
        return result
    
    def _enhance_query_for_people(self, query: str) -> List[str]:
        """Enhance query to find people/portraits"""
        base_queries = []
        
        # Basic query with person filters
        base_queries.append(f"{query} person portrait")
        base_queries.append(f"{query} profile picture")
        
        # If query looks like a location, add specific terms
        location_keywords = ['city', 'town', 'beach', 'mountain', 'park', 'street']
        if any(keyword in query.lower() for keyword in location_keywords):
            base_queries.append(f"people in {query}")
            base_queries.append(f"{query} locals")
        
        # If query looks like an interest/activity
        activity_keywords = ['gym', 'fitness', 'yoga', 'hiking', 'travel', 'coffee', 'art', 'music']
        if any(keyword in query.lower() for keyword in activity_keywords):
            base_queries.append(f"{query} enthusiast")
            base_queries.append(f"{query} lifestyle")
        
        return base_queries[:3]  # Limit to 3 variations to avoid too many requests
    
    def _selenium_image_search(self, query: str, limit: int = 20) -> List[Dict]:
        """Use Selenium to search Google Images"""
        images_data = []
        
        try:
            # Build Google Images search URL with filters for people
            search_url = self._build_google_images_url(query)
            
            self.driver.get(search_url)
            time.sleep(2)
            
            # Accept cookies if prompted
            try:
                accept_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Accept') or contains(text(), 'I agree')]")
                accept_button.click()
                time.sleep(1)
            except NoSuchElementException:
                pass
            
            # Scroll to load more images
            for _ in range(3):  # Limited scrolling
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1.5)
            
            # Find image elements
            image_containers = self.driver.find_elements(By.CSS_SELECTOR, '[data-tbnid]')
            
            for i, container in enumerate(image_containers[:limit]):
                try:
                    # Click to get larger image and metadata
                    container.click()
                    time.sleep(1)
                    
                    image_data = self._extract_image_metadata_selenium()
                    if image_data:
                        images_data.append(image_data)
                    
                    # Close the image preview
                    try:
                        close_button = self.driver.find_element(By.CSS_SELECTOR, '[aria-label="Close"]')
                        close_button.click()
                    except NoSuchElementException:
                        pass
                    
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.debug(f"Error processing image {i}: {e}")
                    continue
            
            self.enforce_rate_limit()
            
        except Exception as e:
            logger.error(f"Selenium Google Images search failed: {e}")
        
        return images_data
    
    def _requests_image_search(self, query: str, limit: int = 20) -> List[Dict]:
        """Use requests to search Google Images (limited functionality)"""
        images_data = []
        
        try:
            search_url = self._build_google_images_url(query)
            self.enforce_rate_limit()
            
            response = self.session.get(search_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract images from the page source
            img_elements = soup.find_all('img')
            
            for i, img in enumerate(img_elements[:limit]):
                try:
                    src = img.get('src') or img.get('data-src')
                    if src and self._is_valid_image_url(src):
                        image_data = {
                            'url': src,
                            'title': img.get('alt', ''),
                            'source_url': search_url,
                            'width': img.get('width'),
                            'height': img.get('height')
                        }
                        images_data.append(image_data)
                        
                except Exception as e:
                    logger.debug(f"Error processing image {i}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Requests Google Images search failed: {e}")
        
        return images_data
    
    def _extract_image_metadata_selenium(self) -> Optional[Dict]:
        """Extract image metadata from Google Images preview"""
        try:
            image_data = {}
            
            # Get image URL
            img_elements = self.driver.find_elements(By.CSS_SELECTOR, 'img[src*="http"]')
            for img in img_elements:
                src = img.get_attribute('src')
                if src and self._is_valid_image_url(src) and 'google' not in src:
                    image_data['url'] = src
                    break
            
            if not image_data.get('url'):
                return None
            
            # Get title/alt text
            try:
                title_element = self.driver.find_element(By.CSS_SELECTOR, '[data-attrid="title"] span')
                image_data['title'] = title_element.text
            except NoSuchElementException:
                pass
            
            # Get source website
            try:
                source_elements = self.driver.find_elements(By.CSS_SELECTOR, '[data-attrid="source"] a')
                if source_elements:
                    image_data['source_url'] = source_elements[0].get_attribute('href')
                    image_data['source_domain'] = urlparse(image_data['source_url']).netloc
            except NoSuchElementException:
                pass
            
            # Get dimensions if available
            try:
                size_element = self.driver.find_element(By.CSS_SELECTOR, '[data-attrid="dimensions"]')
                size_text = size_element.text
                dimensions = re.findall(r'(\d+)\s*×\s*(\d+)', size_text)
                if dimensions:
                    image_data['width'] = int(dimensions[0][0])
                    image_data['height'] = int(dimensions[0][1])
            except (NoSuchElementException, ValueError):
                pass
            
            return image_data if image_data.get('url') else None
            
        except Exception as e:
            logger.debug(f"Error extracting image metadata: {e}")
            return None
    
    def _build_google_images_url(self, query: str) -> str:
        """Build Google Images search URL with filters"""
        base_url = "https://www.google.com/search"
        
        params = {
            'q': query,
            'tbm': 'isch',  # Images search
            'tbs': 'itp:face',  # Filter for faces/people
            'safe': 'moderate',
            'lr': 'lang_en'
        }
        
        # Build URL manually to avoid encoding issues
        param_string = '&'.join([f"{k}={quote_plus(str(v))}" for k, v in params.items()])
        return f"{base_url}?{param_string}"
    
    def _is_valid_image_url(self, url: str) -> bool:
        """Check if URL is a valid image URL"""
        if not url or len(url) < 10:
            return False
            
        # Skip data URLs and low-quality images
        if url.startswith('data:'):
            return False
            
        # Skip Google's own images and thumbnails
        skip_domains = ['google.com', 'gstatic.com', 'googleusercontent.com']
        parsed_url = urlparse(url)
        if any(domain in parsed_url.netloc for domain in skip_domains):
            return False
        
        # Check for image file extensions
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        url_lower = url.lower()
        
        # Either has image extension or looks like an image URL
        return (any(ext in url_lower for ext in image_extensions) or 
                'image' in url_lower or 
                'photo' in url_lower)
    
    def _convert_images_to_profiles(self, images_data: List[Dict]) -> List[ProfileData]:
        """Convert image data to ProfileData objects"""
        profiles = []
        
        for i, img_data in enumerate(images_data):
            try:
                # Generate unique profile ID based on image URL
                image_url = img_data.get('url', '')
                profile_id = hashlib.md5(image_url.encode()).hexdigest()[:12]
                
                profile = ProfileData(
                    source_id=f"gimg_{profile_id}",
                    source_type=SourceType.GOOGLE_IMAGES,
                    url=img_data.get('source_url', ''),
                    name=img_data.get('title', f"Person {i+1}")
                )
                
                # Add image
                profile.profile_images = [image_url]
                profile.image_count = 1
                
                # Extract any bio-like information from title
                title = img_data.get('title', '')
                if title and len(title) > 10:
                    profile.bio = title[:200]  # Limit bio length
                
                # Add metadata
                profile.extra_data = {
                    'source_domain': img_data.get('source_domain', ''),
                    'image_width': img_data.get('width'),
                    'image_height': img_data.get('height'),
                    'search_source': 'google_images'
                }
                
                # Calculate confidence score based on available data
                confidence = 0.3  # Base score for having an image
                if profile.bio:
                    confidence += 0.2
                if img_data.get('width') and img_data.get('height'):
                    if img_data['width'] >= 200 and img_data['height'] >= 200:
                        confidence += 0.2  # Higher quality image
                if img_data.get('source_url'):
                    confidence += 0.1
                
                profile.confidence_score = min(confidence, 1.0)
                profile.is_complete = confidence > 0.5
                
                profiles.append(profile)
                
            except Exception as e:
                logger.debug(f"Error converting image data to profile: {e}")
                continue
        
        return profiles
    
    def get_profile_by_id(self, profile_id: str) -> Optional[ProfileData]:
        """Get specific profile by ID (not applicable for Google Images)"""
        # Google Images doesn't have persistent profile IDs
        # This would require the original image URL
        logger.warning("get_profile_by_id not supported for Google Images scraper")
        return None
    
    def get_profile_images(self, profile: ProfileData) -> List[str]:
        """Get all image URLs for a profile"""
        return profile.profile_images
    
    def normalize_profile_data(self, raw_data: Dict) -> ProfileData:
        """Convert Google Images data to standardized ProfileData"""
        image_url = raw_data.get('url', '')
        profile_id = hashlib.md5(image_url.encode()).hexdigest()[:12]
        
        return ProfileData(
            source_id=f"gimg_{profile_id}",
            source_type=SourceType.GOOGLE_IMAGES,
            url=raw_data.get('source_url', ''),
            name=raw_data.get('title', 'Unknown'),
            bio=raw_data.get('description', ''),
            profile_images=[image_url] if image_url else [],
            image_count=1 if image_url else 0,
            extra_data={
                'source_domain': raw_data.get('source_domain', ''),
                'image_dimensions': f"{raw_data.get('width', 'unknown')}x{raw_data.get('height', 'unknown')}",
                'search_source': 'google_images'
            }
        )
    
    def get_search_suggestions(self, partial_query: str) -> List[str]:
        """Get search suggestions for partial queries"""
        suggestions = []
        
        # Add common people-related search terms
        if len(partial_query) > 2:
            suggestions.extend([
                f"{partial_query} person",
                f"{partial_query} people",
                f"{partial_query} portrait",
                f"{partial_query} profile",
                f"{partial_query} headshot"
            ])
        
        return suggestions[:5]
    
    def close(self):
        """Clean up resources"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Google Images scraper driver closed")
            except Exception as e:
                logger.warning(f"Error closing Google Images scraper driver: {e}")
    
    def __del__(self):
        """Ensure cleanup on deletion"""
        self.close()