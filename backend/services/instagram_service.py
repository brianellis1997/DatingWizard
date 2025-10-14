"""
Instagram Scraping Service

Integrates Instagram scraping with CLIP classification and embedding extraction.
Implements conservative rate limiting for safe automated collection.
"""

import time
import random
import pickle
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from loguru import logger
from PIL import Image
import io

from backend.database.models import InstagramSearch, InstagramResult
from backend.services.classifier_service import get_classifier_service
from backend.config import settings


class InstagramScrapingService:
    """Service for scraping and classifying Instagram profiles"""

    def __init__(self):
        self.classifier_service = get_classifier_service()
        self.screenshots_dir = settings.SCREENSHOTS_DIR / "instagram"
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

        # Rate limiting configuration
        self.min_delay = 5 * 60  # 5 minutes
        self.max_delay = 8 * 60  # 8 minutes
        self.pause_every = 20  # Pause after every N profiles
        self.pause_duration = 60 * 60  # 1 hour pause

        # Scraper will be initialized on first use
        self._scraper = None

    @property
    def scraper(self):
        """Lazy-load Instagram scraper"""
        if self._scraper is None:
            from src.scrapers.instagram_scraper import InstagramScraper
            self._scraper = InstagramScraper(use_selenium=True, headless=True)
            logger.info("Instagram scraper initialized")
        return self._scraper

    def scrape_profile_by_username(
        self,
        username: str,
        db_session,
        search_id: Optional[int] = None
    ) -> Optional[InstagramResult]:
        """
        Scrape a single Instagram profile by username.

        Args:
            username: Instagram username to scrape
            db_session: SQLAlchemy database session
            search_id: Optional search session ID to link this result

        Returns:
            InstagramResult object or None if failed
        """
        try:
            logger.info(f"Scraping Instagram profile: {username}")

            # Get profile data from scraper
            profile_data = self.scraper.get_profile_by_id(username)

            if not profile_data:
                logger.warning(f"Failed to scrape profile: {username}")
                return None

            # Take screenshot of profile
            screenshot_path = self._screenshot_profile(username)

            if not screenshot_path:
                logger.warning(f"Failed to screenshot profile: {username}")
                return None

            # Classify with CLIP
            classification_result = self.classifier_service.classify_screenshot(str(screenshot_path))

            # Extract embedding
            embedding = self.classifier_service.classifier.extract_embedding(str(screenshot_path))
            image_embedding = pickle.dumps(embedding) if embedding is not None else None

            # Create Instagram result
            instagram_result = InstagramResult(
                search_id=search_id,
                username=username,
                name=profile_data.name,
                bio=profile_data.bio,
                url=profile_data.url,
                followers=profile_data.followers,
                profile_image_url=profile_data.profile_images[0] if profile_data.profile_images else None,
                screenshot_path=str(screenshot_path),
                image_embedding=image_embedding,
                embedding_model_version="openai/clip-vit-base-patch32" if image_embedding else None,
                confidence_score=classification_result.confidence_score,
                physical_score=classification_result.component_scores['physical'],
                personality_score=classification_result.component_scores['personality'],
                interest_score=classification_result.component_scores['interests'],
                is_match=classification_result.is_match
            )

            db_session.add(instagram_result)
            db_session.commit()
            db_session.refresh(instagram_result)

            logger.info(f"Successfully scraped and classified {username} - Match: {instagram_result.is_match} "
                       f"(Confidence: {instagram_result.confidence_score:.2%})")

            return instagram_result

        except Exception as e:
            logger.error(f"Error scraping profile {username}: {e}")
            db_session.rollback()
            return None

    def scrape_hashtag(
        self,
        hashtag: str,
        db_session,
        limit: int = 20,
        min_score: float = 0.6
    ) -> InstagramSearch:
        """
        Scrape profiles from a hashtag search with conservative rate limiting.

        NOTE: ALL profiles are stored regardless of score for active learning.
        The min_score is just metadata - it doesn't filter results.

        Args:
            hashtag: Hashtag to search (without # symbol)
            db_session: SQLAlchemy database session
            limit: Maximum number of profiles to scrape
            min_score: Stored as metadata only (not used for filtering)

        Returns:
            InstagramSearch object with results
        """
        try:
            logger.info(f"Starting hashtag search: #{hashtag} (limit: {limit})")

            # Create search session
            search_session = InstagramSearch(
                query=hashtag,
                limit=limit,
                min_score=min_score
            )
            db_session.add(search_session)
            db_session.commit()
            db_session.refresh(search_session)

            # Search for profiles using hashtag
            search_result = self.scraper.search_profiles(hashtag, limit=limit * 2)  # Get extra to filter

            if not search_result.profiles:
                logger.warning(f"No profiles found for hashtag #{hashtag}")
                search_session.total_found = 0
                search_session.matches_found = 0
                db_session.commit()
                return search_session

            logger.info(f"Found {len(search_result.profiles)} profiles from hashtag #{hashtag}")

            # Process each profile with rate limiting
            processed_count = 0
            matches_count = 0

            for i, profile_data in enumerate(search_result.profiles[:limit]):
                try:
                    # Conservative rate limiting
                    if processed_count > 0:
                        delay = random.uniform(self.min_delay, self.max_delay)
                        logger.info(f"Rate limiting: waiting {delay/60:.1f} minutes before next profile...")
                        time.sleep(delay)

                    # Long pause every N profiles
                    if processed_count > 0 and processed_count % self.pause_every == 0:
                        logger.info(f"Taking {self.pause_duration/3600:.1f} hour break after {processed_count} profiles...")
                        time.sleep(self.pause_duration)

                    # Scrape and classify profile
                    username = profile_data.source_id
                    result = self.scrape_profile_by_username(username, db_session, search_session.id)

                    if result:
                        processed_count += 1
                        if result.is_match:
                            matches_count += 1

                        logger.info(f"Progress: {processed_count}/{limit} profiles processed, "
                                   f"{matches_count} matches found")

                except Exception as e:
                    logger.error(f"Error processing profile {i+1}: {e}")
                    continue

            # Update search session with final counts
            search_session.total_found = processed_count
            search_session.matches_found = matches_count
            db_session.commit()

            logger.info(f"Hashtag search complete: {processed_count} profiles processed, "
                       f"{matches_count} matches found")

            return search_session

        except Exception as e:
            logger.error(f"Error in hashtag search: {e}")
            db_session.rollback()
            raise

    def scrape_multiple_hashtags(
        self,
        hashtags: List[str],
        db_session,
        profiles_per_hashtag: int = 20,
        min_score: float = 0.6
    ) -> List[InstagramSearch]:
        """
        Scrape profiles from multiple hashtags sequentially.

        Args:
            hashtags: List of hashtags to search
            db_session: SQLAlchemy database session
            profiles_per_hashtag: Number of profiles to scrape per hashtag
            min_score: Minimum confidence score

        Returns:
            List of InstagramSearch objects
        """
        results = []

        for hashtag in hashtags:
            try:
                search_result = self.scrape_hashtag(
                    hashtag=hashtag,
                    db_session=db_session,
                    limit=profiles_per_hashtag,
                    min_score=min_score
                )
                results.append(search_result)

            except Exception as e:
                logger.error(f"Failed to scrape hashtag #{hashtag}: {e}")
                continue

        return results

    def _screenshot_profile(self, username: str) -> Optional[Path]:
        """
        Take a screenshot of an Instagram profile.

        Args:
            username: Instagram username

        Returns:
            Path to screenshot file or None if failed
        """
        try:
            url = f"https://www.instagram.com/{username}/"

            # Navigate to profile
            self.scraper.driver.get(url)
            time.sleep(3)  # Wait for page to load

            # Take screenshot
            screenshot_bytes = self.scraper.driver.get_screenshot_as_png()

            # Save screenshot
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{username}_{timestamp}.png"
            screenshot_path = self.screenshots_dir / filename

            with open(screenshot_path, 'wb') as f:
                f.write(screenshot_bytes)

            logger.info(f"Screenshot saved: {screenshot_path}")
            return screenshot_path

        except Exception as e:
            logger.error(f"Error taking screenshot of {username}: {e}")
            return None

    def get_search_results(
        self,
        db_session,
        search_id: int
    ) -> List[InstagramResult]:
        """
        Get all results for a search session.

        Args:
            db_session: SQLAlchemy database session
            search_id: Search session ID

        Returns:
            List of InstagramResult objects
        """
        return db_session.query(InstagramResult).filter(
            InstagramResult.search_id == search_id
        ).order_by(InstagramResult.confidence_score.desc()).all()

    def get_matches(
        self,
        db_session,
        skip: int = 0,
        limit: int = 20
    ) -> List[InstagramResult]:
        """
        Get all matches from Instagram scraping.

        Args:
            db_session: SQLAlchemy database session
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of InstagramResult objects marked as matches
        """
        return db_session.query(InstagramResult).filter(
            InstagramResult.is_match == True
        ).order_by(
            InstagramResult.confidence_score.desc()
        ).offset(skip).limit(limit).all()

    def submit_feedback(
        self,
        db_session,
        result_id: int,
        feedback: str
    ) -> Optional[InstagramResult]:
        """
        Submit user feedback for an Instagram result.

        Args:
            db_session: SQLAlchemy database session
            result_id: Instagram result ID
            feedback: Feedback type ('like', 'dislike', 'super_like')

        Returns:
            Updated InstagramResult or None if not found
        """
        result = db_session.query(InstagramResult).filter(
            InstagramResult.id == result_id
        ).first()

        if not result:
            return None

        result.user_feedback = feedback
        result.feedback_at = datetime.now()

        db_session.commit()
        db_session.refresh(result)

        logger.info(f"Feedback '{feedback}' submitted for Instagram result {result_id}")
        return result

    def remove_feedback(
        self,
        db_session,
        result_id: int
    ) -> Optional[InstagramResult]:
        """
        Remove user feedback from an Instagram result.

        Args:
            db_session: SQLAlchemy database session
            result_id: Instagram result ID

        Returns:
            Updated InstagramResult or None if not found
        """
        result = db_session.query(InstagramResult).filter(
            InstagramResult.id == result_id
        ).first()

        if not result:
            return None

        result.user_feedback = None
        result.feedback_at = None

        db_session.commit()
        db_session.refresh(result)

        logger.info(f"Feedback removed from Instagram result {result_id}")
        return result

    def close(self):
        """Clean up resources"""
        if self._scraper:
            self._scraper.close()
            logger.info("Instagram scraper closed")


# Singleton instance
_instagram_service = None


def get_instagram_service() -> InstagramScrapingService:
    """Get or create singleton Instagram service instance"""
    global _instagram_service
    if _instagram_service is None:
        _instagram_service = InstagramScrapingService()
    return _instagram_service
