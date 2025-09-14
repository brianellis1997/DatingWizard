"""
Base Profile Scraper - Abstract base class for all profile scrapers
Provides common interface and functionality for different sources
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Iterator, Any
from enum import Enum
import time
import hashlib
from datetime import datetime
from loguru import logger


class SourceType(Enum):
    """Types of profile sources"""
    TINDER = "tinder"
    INSTAGRAM = "instagram" 
    GOOGLE_IMAGES = "google_images"
    FACEBOOK = "facebook"
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    CUSTOM = "custom"


@dataclass
class ProfileData:
    """Standardized profile data structure"""
    # Core identification
    source_id: str  # Unique ID from source platform
    source_type: SourceType
    url: Optional[str] = None
    
    # Personal info
    name: Optional[str] = None
    age: Optional[int] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    
    # Images
    profile_images: List[str] = field(default_factory=list)  # URLs
    image_count: int = 0
    
    # Social info
    followers: Optional[int] = None
    following: Optional[int] = None
    verified: bool = False
    
    # Interests and metadata
    interests: List[str] = field(default_factory=list)
    hashtags: List[str] = field(default_factory=list)
    occupation: Optional[str] = None
    education: Optional[str] = None
    
    # Scraping metadata
    scraped_at: datetime = field(default_factory=datetime.now)
    confidence_score: float = 1.0  # How confident we are in data quality
    is_complete: bool = False  # Whether we got full profile data
    
    # Additional platform-specific data
    extra_data: Dict[str, Any] = field(default_factory=dict)
    
    def get_unique_hash(self) -> str:
        """Generate unique hash for deduplication"""
        # Use source + source_id + name for hashing
        hash_string = f"{self.source_type.value}:{self.source_id}:{self.name or 'unknown'}"
        return hashlib.md5(hash_string.encode()).hexdigest()[:12]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        data = {
            'source_id': self.source_id,
            'source_type': self.source_type.value,
            'url': self.url,
            'name': self.name,
            'age': self.age,
            'location': self.location,
            'bio': self.bio,
            'profile_images': self.profile_images,
            'image_count': self.image_count,
            'followers': self.followers,
            'following': self.following,
            'verified': self.verified,
            'interests': self.interests,
            'hashtags': self.hashtags,
            'occupation': self.occupation,
            'education': self.education,
            'scraped_at': self.scraped_at.isoformat(),
            'confidence_score': self.confidence_score,
            'is_complete': self.is_complete,
            'extra_data': self.extra_data,
            'unique_hash': self.get_unique_hash()
        }
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ProfileData':
        """Create ProfileData from dictionary"""
        # Handle datetime conversion
        scraped_at = data.get('scraped_at')
        if isinstance(scraped_at, str):
            scraped_at = datetime.fromisoformat(scraped_at)
        elif scraped_at is None:
            scraped_at = datetime.now()
            
        return cls(
            source_id=data['source_id'],
            source_type=SourceType(data['source_type']),
            url=data.get('url'),
            name=data.get('name'),
            age=data.get('age'),
            location=data.get('location'),
            bio=data.get('bio'),
            profile_images=data.get('profile_images', []),
            image_count=data.get('image_count', 0),
            followers=data.get('followers'),
            following=data.get('following'),
            verified=data.get('verified', False),
            interests=data.get('interests', []),
            hashtags=data.get('hashtags', []),
            occupation=data.get('occupation'),
            education=data.get('education'),
            scraped_at=scraped_at,
            confidence_score=data.get('confidence_score', 1.0),
            is_complete=data.get('is_complete', False),
            extra_data=data.get('extra_data', {})
        )


@dataclass
class ScrapingResult:
    """Result of a scraping operation"""
    profiles: List[ProfileData] = field(default_factory=list)
    total_found: int = 0
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    error_messages: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    rate_limited: bool = False
    next_cursor: Optional[str] = None  # For pagination
    
    def add_profile(self, profile: ProfileData) -> None:
        """Add a successfully scraped profile"""
        self.profiles.append(profile)
        self.successful += 1
        
    def add_error(self, error_msg: str) -> None:
        """Add an error message"""
        self.error_messages.append(error_msg)
        self.failed += 1
        
    def skip_profile(self, reason: str = "") -> None:
        """Mark a profile as skipped"""
        self.skipped += 1
        if reason:
            self.error_messages.append(f"Skipped: {reason}")


class ProfileScraper(ABC):
    """Abstract base class for all profile scrapers"""
    
    def __init__(self, rate_limit_delay: float = 1.0, max_retries: int = 3):
        self.rate_limit_delay = rate_limit_delay
        self.max_retries = max_retries
        self.last_request_time = 0.0
        self.request_count = 0
        self.source_type = self.get_source_type()
        
    @abstractmethod
    def get_source_type(self) -> SourceType:
        """Return the source type this scraper handles"""
        pass
    
    @abstractmethod
    def search_profiles(self, query: str, limit: int = 50, **kwargs) -> ScrapingResult:
        """Search for profiles based on query"""
        pass
    
    @abstractmethod
    def get_profile_by_id(self, profile_id: str) -> Optional[ProfileData]:
        """Get specific profile by ID"""
        pass
    
    @abstractmethod
    def get_profile_images(self, profile: ProfileData) -> List[str]:
        """Get all image URLs for a profile"""
        pass
    
    def validate_profile(self, profile: ProfileData) -> bool:
        """Validate that profile has minimum required data"""
        if not profile.source_id:
            return False
        if not profile.name and not profile.bio:
            return False
        if not profile.profile_images:
            return False
        return True
    
    def enforce_rate_limit(self) -> None:
        """Enforce rate limiting between requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
            
        self.last_request_time = time.time()
        self.request_count += 1
    
    def retry_on_failure(self, func, *args, **kwargs):
        """Retry a function call on failure"""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"All {self.max_retries} attempts failed: {e}")
        
        raise last_error
    
    def normalize_profile_data(self, raw_data: Dict) -> ProfileData:
        """Convert platform-specific data to standardized ProfileData"""
        # This should be implemented by each scraper based on their data format
        raise NotImplementedError("Subclasses must implement normalize_profile_data")
    
    def get_search_suggestions(self, partial_query: str) -> List[str]:
        """Get search suggestions for partial queries (optional)"""
        return []
    
    def get_rate_limit_info(self) -> Dict:
        """Get current rate limit status"""
        return {
            'request_count': self.request_count,
            'rate_limit_delay': self.rate_limit_delay,
            'last_request_time': self.last_request_time
        }
    
    def reset_rate_limit(self) -> None:
        """Reset rate limit counters"""
        self.request_count = 0
        self.last_request_time = 0.0
        
    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.source_type.value})"