"""
Classifier Service - Wraps the DatingClassifier for API use with database integration
"""

import sys
import os
from pathlib import Path
from typing import Dict, List
from PIL import Image
from sqlalchemy.orm import Session

# Add src to path to import existing classifier
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.analyzers.dating_classifier import DatingClassifier, ClassificationResult as CLIClassificationResult
from backend.config import settings
from backend.database.db import SessionLocal
from backend.database.models import ReferenceImage, PersonalityTrait, SharedInterest, Preference
from loguru import logger


class DatabaseAwareClassifier(DatingClassifier):
    """Extended classifier that loads training data from database"""

    def __init__(self, db: Session):
        """Initialize with database session"""
        self.db = db
        # Initialize parent without loading from preferences file
        self.preferences = self._load_preferences_from_db()

        # Initialize image analysis
        self.image_model = self._initialize_image_model()
        self.transform = self._get_image_transform()

        # Load reference features
        self.reference_features = []
        self.positive_examples = []
        self.negative_examples = []

        self._load_all_training_data()

        logger.info(f"Loaded {len(self.reference_features)} reference images from database")
        logger.info(f"Loaded {len(self.positive_examples)} positive examples")
        logger.info(f"Loaded {len(self.negative_examples)} negative examples")

    def _load_preferences_from_db(self) -> Dict:
        """Load preferences from database"""
        pref = self.db.query(Preference).first()

        if not pref:
            return {
                'partner_preferences': {
                    'physical': {'importance_weight': 0.6},
                    'personality': {'importance_weight': 0.3, 'traits': []},
                    'interests': {'importance_weight': 0.1, 'shared_interests': [], 'dealbreaker_interests': []}
                },
                'matching_criteria': {
                    'minimum_score': 0.6,
                    'super_like_score': 0.85
                },
                'age_range': {
                    'min': 18,
                    'max': 99
                }
            }

        # Load personality traits
        traits = self.db.query(PersonalityTrait).all()
        trait_list = [t.trait for t in traits]

        # Load interests
        interests = self.db.query(SharedInterest).filter_by(is_dealbreaker=False).all()
        interest_list = [i.interest for i in interests]

        dealbreakers = self.db.query(SharedInterest).filter_by(is_dealbreaker=True).all()
        dealbreaker_list = [d.interest for d in dealbreakers]

        return {
            'partner_preferences': {
                'physical': {'importance_weight': pref.physical_weight},
                'personality': {'importance_weight': pref.personality_weight, 'traits': trait_list},
                'interests': {
                    'importance_weight': pref.interest_weight,
                    'shared_interests': interest_list,
                    'dealbreaker_interests': dealbreaker_list
                }
            },
            'matching_criteria': {
                'minimum_score': pref.min_score,
                'super_like_score': pref.super_like_score
            },
            'age_range': {
                'min': pref.age_min,
                'max': pref.age_max
            }
        }

    def _load_all_training_data(self):
        """Load training data from database instead of files"""
        # Load reference images from database
        try:
            ref_images = self.db.query(ReferenceImage).all()
            logger.info(f"Found {len(ref_images)} reference images in database")

            for ref_img in ref_images:
                logger.debug(f"Loading reference image: {ref_img.file_path}")
                features = self._extract_image_features(ref_img.file_path)
                if features is not None:
                    self.reference_features.append({
                        'features': features,
                        'category': ref_img.category,
                        'description': ref_img.description,
                        'id': ref_img.id
                    })
                    logger.debug(f"Successfully loaded features for image {ref_img.id}")
                else:
                    logger.warning(f"Failed to extract features from {ref_img.file_path}")
        except Exception as e:
            logger.error(f"Failed to load reference images from database: {e}")

        # Load positive/negative examples from file system (legacy)
        liked_dir = "config/liked_profiles"
        if os.path.exists(liked_dir):
            for img_file in os.listdir(liked_dir):
                if img_file.endswith(('.jpg', '.png', '.jpeg')):
                    img_path = os.path.join(liked_dir, img_file)
                    features = self._extract_image_features(img_path)
                    if features is not None:
                        self.positive_examples.append(features)

        disliked_dir = "config/disliked_profiles"
        if os.path.exists(disliked_dir):
            for img_file in os.listdir(disliked_dir):
                if img_file.endswith(('.jpg', '.png', '.jpeg')):
                    img_path = os.path.join(disliked_dir, img_file)
                    features = self._extract_image_features(img_path)
                    if features is not None:
                        self.negative_examples.append(features)


class ClassifierService:
    """Service for managing the DatingClassifier"""

    def __init__(self):
        """Initialize the classifier"""
        self.classifier = None
        self.db_session = None
        self._init_classifier()

    def _init_classifier(self):
        """Initialize or reinitialize the classifier"""
        try:
            # Close previous session if exists
            if self.db_session:
                self.db_session.close()

            # Create new session
            self.db_session = SessionLocal()
            self.classifier = DatabaseAwareClassifier(self.db_session)
            logger.info("Database-aware classifier initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize classifier: {e}")
            if self.db_session:
                self.db_session.close()
            raise

    def reload_classifier(self):
        """Reload the classifier (useful after preference updates)"""
        self._init_classifier()

    def __del__(self):
        """Cleanup database session"""
        if self.db_session:
            self.db_session.close()

    def classify_screenshot(self, screenshot_path: str) -> CLIClassificationResult:
        """
        Classify a single screenshot

        Args:
            screenshot_path: Path to screenshot image

        Returns:
            ClassificationResult object
        """
        if not self.classifier:
            raise RuntimeError("Classifier not initialized")

        return self.classifier.classify_screenshot(screenshot_path)

    def classify_batch(self, screenshot_paths: List[str]) -> List[CLIClassificationResult]:
        """
        Classify multiple screenshots

        Args:
            screenshot_paths: List of screenshot paths

        Returns:
            List of ClassificationResult objects
        """
        if not self.classifier:
            raise RuntimeError("Classifier not initialized")

        return self.classifier.batch_classify(screenshot_paths)

    def get_stats(self) -> Dict:
        """Get classifier statistics"""
        if not self.classifier:
            raise RuntimeError("Classifier not initialized")

        return self.classifier.get_classifier_stats()

    def create_thumbnail(self, image_path: str, size: tuple = (200, 200)) -> str:
        """
        Create a thumbnail for an image

        Args:
            image_path: Path to original image
            size: Thumbnail size (width, height)

        Returns:
            Path to thumbnail
        """
        try:
            img = Image.open(image_path)

            # Convert to RGB if necessary
            if img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGB')

            # Create thumbnail
            img.thumbnail(size, Image.Resampling.LANCZOS)

            # Save thumbnail
            filename = Path(image_path).name
            thumbnail_path = settings.THUMBNAILS_DIR / filename

            img.save(thumbnail_path, 'JPEG', quality=85)

            return str(thumbnail_path)

        except Exception as e:
            logger.error(f"Failed to create thumbnail for {image_path}: {e}")
            return None


# Singleton instance
_classifier_service = None


def get_classifier_service() -> ClassifierService:
    """Get or create classifier service instance"""
    global _classifier_service

    if _classifier_service is None:
        _classifier_service = ClassifierService()

    return _classifier_service
