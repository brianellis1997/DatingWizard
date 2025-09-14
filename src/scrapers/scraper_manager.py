"""
Scraper Manager - Manages multiple profile scrapers and coordinates scraping operations
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Iterator, Type
from datetime import datetime, timedelta
from loguru import logger

from .base_scraper import ProfileScraper, ProfileData, ScrapingResult, SourceType


class ScraperManager:
    """Manages multiple scrapers and provides unified interface"""
    
    def __init__(self, data_dir: str = "data/scraped_profiles"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self.db_path = self.data_dir / "profiles.db"
        self._init_database()
        
        # Registry of available scrapers
        self.scrapers: Dict[SourceType, ProfileScraper] = {}
        self.scraper_classes: Dict[str, Type[ProfileScraper]] = {}
        
        # Caching
        self.cache_duration = timedelta(hours=24)  # Cache for 24 hours
        
    def _init_database(self):
        """Initialize SQLite database for profile storage"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    unique_hash TEXT UNIQUE,
                    source_type TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    name TEXT,
                    age INTEGER,
                    location TEXT,
                    bio TEXT,
                    profile_images TEXT,  -- JSON array
                    image_count INTEGER,
                    followers INTEGER,
                    following INTEGER,
                    verified BOOLEAN,
                    interests TEXT,  -- JSON array
                    hashtags TEXT,   -- JSON array
                    occupation TEXT,
                    education TEXT,
                    scraped_at TIMESTAMP,
                    confidence_score REAL,
                    is_complete BOOLEAN,
                    extra_data TEXT,  -- JSON
                    url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS scraping_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_type TEXT NOT NULL,
                    query TEXT,
                    total_found INTEGER,
                    successful INTEGER,
                    failed INTEGER,
                    skipped INTEGER,
                    execution_time REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    error_messages TEXT  -- JSON array
                )
            ''')
            
            # Create indexes
            conn.execute('CREATE INDEX IF NOT EXISTS idx_source_type ON profiles(source_type)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_unique_hash ON profiles(unique_hash)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_scraped_at ON profiles(scraped_at)')
    
    def register_scraper(self, scraper: ProfileScraper) -> None:
        """Register a scraper for a specific source type"""
        source_type = scraper.get_source_type()
        self.scrapers[source_type] = scraper
        logger.info(f"Registered scraper for {source_type.value}")
    
    def register_scraper_class(self, name: str, scraper_class: Type[ProfileScraper]) -> None:
        """Register a scraper class that can be instantiated later"""
        self.scraper_classes[name] = scraper_class
        logger.info(f"Registered scraper class: {name}")
    
    def get_scraper(self, source_type: SourceType) -> Optional[ProfileScraper]:
        """Get scraper for specific source type"""
        return self.scrapers.get(source_type)
    
    def get_available_sources(self) -> List[SourceType]:
        """Get list of available source types"""
        return list(self.scrapers.keys())
    
    def search_all_sources(self, query: str, limit_per_source: int = 20, 
                          sources: Optional[List[SourceType]] = None) -> Dict[SourceType, ScrapingResult]:
        """Search across multiple sources"""
        if sources is None:
            sources = self.get_available_sources()
            
        results = {}
        
        for source_type in sources:
            scraper = self.get_scraper(source_type)
            if not scraper:
                logger.warning(f"No scraper available for {source_type.value}")
                continue
                
            try:
                logger.info(f"Searching {source_type.value} for: {query}")
                result = scraper.search_profiles(query, limit=limit_per_source)
                results[source_type] = result
                
                # Store results in database
                self._store_profiles(result.profiles)
                self._store_session(source_type, query, result)
                
                logger.info(f"{source_type.value}: found {result.successful} profiles")
                
            except Exception as e:
                logger.error(f"Error scraping {source_type.value}: {e}")
                results[source_type] = ScrapingResult(error_messages=[str(e)])
        
        return results
    
    def search_source(self, source_type: SourceType, query: str, 
                     limit: int = 50, **kwargs) -> Optional[ScrapingResult]:
        """Search a specific source"""
        scraper = self.get_scraper(source_type)
        if not scraper:
            logger.error(f"No scraper available for {source_type.value}")
            return None
            
        try:
            result = scraper.search_profiles(query, limit=limit, **kwargs)
            
            # Store results
            self._store_profiles(result.profiles)
            self._store_session(source_type, query, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error scraping {source_type.value}: {e}")
            return ScrapingResult(error_messages=[str(e)])
    
    def get_profile_by_id(self, source_type: SourceType, profile_id: str) -> Optional[ProfileData]:
        """Get specific profile by ID from source or database"""
        # First check database
        cached_profile = self._get_cached_profile(source_type, profile_id)
        if cached_profile:
            logger.debug(f"Found cached profile: {profile_id}")
            return cached_profile
            
        # If not in cache, scrape it
        scraper = self.get_scraper(source_type)
        if scraper:
            try:
                profile = scraper.get_profile_by_id(profile_id)
                if profile:
                    self._store_profiles([profile])
                    return profile
            except Exception as e:
                logger.error(f"Error getting profile {profile_id}: {e}")
        
        return None
    
    def get_cached_profiles(self, source_type: Optional[SourceType] = None, 
                          max_age_hours: Optional[int] = None) -> List[ProfileData]:
        """Get profiles from local database cache"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            query = "SELECT * FROM profiles"
            params = []
            
            conditions = []
            if source_type:
                conditions.append("source_type = ?")
                params.append(source_type.value)
                
            if max_age_hours:
                cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
                conditions.append("scraped_at > ?")
                params.append(cutoff_time.isoformat())
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
                
            query += " ORDER BY scraped_at DESC"
            
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            profiles = []
            for row in rows:
                try:
                    profile_data = {
                        'source_id': row['source_id'],
                        'source_type': row['source_type'],
                        'url': row['url'],
                        'name': row['name'],
                        'age': row['age'],
                        'location': row['location'],
                        'bio': row['bio'],
                        'profile_images': json.loads(row['profile_images'] or '[]'),
                        'image_count': row['image_count'] or 0,
                        'followers': row['followers'],
                        'following': row['following'],
                        'verified': bool(row['verified']),
                        'interests': json.loads(row['interests'] or '[]'),
                        'hashtags': json.loads(row['hashtags'] or '[]'),
                        'occupation': row['occupation'],
                        'education': row['education'],
                        'scraped_at': row['scraped_at'],
                        'confidence_score': row['confidence_score'] or 1.0,
                        'is_complete': bool(row['is_complete']),
                        'extra_data': json.loads(row['extra_data'] or '{}')
                    }
                    
                    profile = ProfileData.from_dict(profile_data)
                    profiles.append(profile)
                    
                except Exception as e:
                    logger.warning(f"Error parsing profile from database: {e}")
                    continue
                    
            return profiles
    
    def deduplicate_profiles(self, profiles: List[ProfileData]) -> List[ProfileData]:
        """Remove duplicate profiles based on unique hash"""
        seen_hashes = set()
        unique_profiles = []
        
        for profile in profiles:
            profile_hash = profile.get_unique_hash()
            if profile_hash not in seen_hashes:
                seen_hashes.add(profile_hash)
                unique_profiles.append(profile)
            else:
                logger.debug(f"Skipping duplicate profile: {profile.name}")
                
        logger.info(f"Deduplicated {len(profiles)} -> {len(unique_profiles)} profiles")
        return unique_profiles
    
    def get_scraping_stats(self, days: int = 7) -> Dict:
        """Get scraping statistics"""
        cutoff_time = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            # Profile stats
            cursor = conn.execute('''
                SELECT source_type, COUNT(*) as count
                FROM profiles 
                WHERE created_at > ? 
                GROUP BY source_type
            ''', (cutoff_time.isoformat(),))
            
            profile_stats = dict(cursor.fetchall())
            
            # Session stats
            cursor = conn.execute('''
                SELECT source_type, 
                       COUNT(*) as sessions,
                       SUM(successful) as total_successful,
                       SUM(failed) as total_failed,
                       AVG(execution_time) as avg_time
                FROM scraping_sessions 
                WHERE created_at > ?
                GROUP BY source_type
            ''', (cutoff_time.isoformat(),))
            
            session_stats = {}
            for row in cursor.fetchall():
                source_type, sessions, successful, failed, avg_time = row
                session_stats[source_type] = {
                    'sessions': sessions,
                    'successful': successful or 0,
                    'failed': failed or 0,
                    'avg_execution_time': avg_time or 0
                }
        
        return {
            'profile_counts': profile_stats,
            'session_stats': session_stats,
            'total_profiles': sum(profile_stats.values()),
            'days': days
        }
    
    def _store_profiles(self, profiles: List[ProfileData]) -> None:
        """Store profiles in database"""
        if not profiles:
            return
            
        with sqlite3.connect(self.db_path) as conn:
            for profile in profiles:
                try:
                    conn.execute('''
                        INSERT OR REPLACE INTO profiles (
                            unique_hash, source_type, source_id, name, age, location, bio,
                            profile_images, image_count, followers, following, verified,
                            interests, hashtags, occupation, education, scraped_at,
                            confidence_score, is_complete, extra_data, url
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        profile.get_unique_hash(),
                        profile.source_type.value,
                        profile.source_id,
                        profile.name,
                        profile.age,
                        profile.location,
                        profile.bio,
                        json.dumps(profile.profile_images),
                        profile.image_count,
                        profile.followers,
                        profile.following,
                        profile.verified,
                        json.dumps(profile.interests),
                        json.dumps(profile.hashtags),
                        profile.occupation,
                        profile.education,
                        profile.scraped_at.isoformat(),
                        profile.confidence_score,
                        profile.is_complete,
                        json.dumps(profile.extra_data),
                        profile.url
                    ))
                except Exception as e:
                    logger.error(f"Error storing profile {profile.source_id}: {e}")
    
    def _store_session(self, source_type: SourceType, query: str, result: ScrapingResult) -> None:
        """Store scraping session info"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO scraping_sessions (
                    source_type, query, total_found, successful, failed, skipped,
                    execution_time, error_messages
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                source_type.value,
                query,
                result.total_found,
                result.successful,
                result.failed,
                result.skipped,
                result.execution_time,
                json.dumps(result.error_messages)
            ))
    
    def _get_cached_profile(self, source_type: SourceType, profile_id: str) -> Optional[ProfileData]:
        """Get profile from cache if not expired"""
        cutoff_time = datetime.now() - self.cache_duration
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM profiles 
                WHERE source_type = ? AND source_id = ? AND scraped_at > ?
            ''', (source_type.value, profile_id, cutoff_time.isoformat()))
            
            row = cursor.fetchone()
            if row:
                try:
                    profile_data = {
                        'source_id': row['source_id'],
                        'source_type': row['source_type'],
                        'url': row['url'],
                        'name': row['name'],
                        'age': row['age'],
                        'location': row['location'],
                        'bio': row['bio'],
                        'profile_images': json.loads(row['profile_images'] or '[]'),
                        'image_count': row['image_count'] or 0,
                        'followers': row['followers'],
                        'following': row['following'],
                        'verified': bool(row['verified']),
                        'interests': json.loads(row['interests'] or '[]'),
                        'hashtags': json.loads(row['hashtags'] or '[]'),
                        'occupation': row['occupation'],
                        'education': row['education'],
                        'scraped_at': row['scraped_at'],
                        'confidence_score': row['confidence_score'] or 1.0,
                        'is_complete': bool(row['is_complete']),
                        'extra_data': json.loads(row['extra_data'] or '{}')
                    }
                    return ProfileData.from_dict(profile_data)
                except Exception as e:
                    logger.error(f"Error parsing cached profile: {e}")
        
        return None
    
    def cleanup_old_profiles(self, max_age_days: int = 30) -> int:
        """Clean up old profiles from database"""
        cutoff_time = datetime.now() - timedelta(days=max_age_days)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('DELETE FROM profiles WHERE scraped_at < ?', 
                                (cutoff_time.isoformat(),))
            deleted_count = cursor.rowcount
            
            # Also clean up old sessions
            cursor = conn.execute('DELETE FROM scraping_sessions WHERE created_at < ?',
                                (cutoff_time.isoformat(),))
            
        logger.info(f"Cleaned up {deleted_count} old profiles")
        return deleted_count