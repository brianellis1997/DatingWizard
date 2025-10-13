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
from src.analyzers.clip_classifier import CLIPClassifier
from backend.config import settings
from backend.database.db import SessionLocal
from backend.database.models import ReferenceImage, PersonalityTrait, SharedInterest, Preference
from loguru import logger


class DatabaseAwareCLIPClassifier(CLIPClassifier):
    """CLIP classifier that loads training data from database"""

    def __init__(self, db: Session, model_name: str = None):
        """Initialize with database session"""
        self.db = db

        # Don't call parent __init__ yet - we need to set up preferences first
        # Initialize CLIP model and processor
        import torch
        from transformers import CLIPProcessor, CLIPModel as HFCLIPModel

        model_name = model_name or settings.CLIP_MODEL_NAME
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Initializing CLIP ({model_name}) on device: {self.device}")

        self.model = HFCLIPModel.from_pretrained(model_name).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        self.model.eval()

        # Load preferences from database
        self.preferences = self._load_preferences_from_db()

        # Load reference features
        self.reference_features = []
        self.reference_text_features = []
        self.positive_examples = []
        self.negative_examples = []

        # Create a mock pref_manager that redirects to our methods
        class MockPrefManager:
            def __init__(self, parent):
                self.parent = parent

            def get_personality_traits(self):
                return self.parent.get_personality_traits()

            def get_shared_interests(self):
                return self.parent.get_shared_interests()

            def get_reference_images(self):
                return []  # Not needed, we load from DB directly

        self.pref_manager = MockPrefManager(self)

        self._load_all_training_data_from_db()

        logger.info(f"✅ CLIP classifier loaded {len(self.reference_features)} reference images from database")
        logger.info(f"Loaded {len(self.positive_examples)} positive examples")
        logger.info(f"Loaded {len(self.negative_examples)} negative examples")

    def _load_preferences_from_db(self) -> Dict:
        """Load preferences from database in CLIP-compatible format"""
        pref = self.db.query(Preference).first()

        # Load personality traits
        traits = self.db.query(PersonalityTrait).all()
        trait_list = [{'trait': t.trait} for t in traits]

        # Load interests
        interests = self.db.query(SharedInterest).all()
        interest_list = [{'interest': i.interest, 'is_dealbreaker': i.is_dealbreaker} for i in interests]

        if not pref:
            return {
                'scoring_weights': {
                    'physical': 0.6,
                    'personality': 0.3,
                    'interests': 0.1
                },
                'min_score': 0.6,
                'super_like_score': 0.85,
                'personality_traits': trait_list,
                'shared_interests': interest_list
            }

        return {
            'scoring_weights': {
                'physical': pref.physical_weight,
                'personality': pref.personality_weight,
                'interests': pref.interest_weight
            },
            'min_score': pref.min_score,
            'super_like_score': pref.super_like_score,
            'personality_traits': trait_list,
            'shared_interests': interest_list
        }

    def _load_all_training_data_from_db(self):
        """Load training data from database"""
        try:
            ref_images = self.db.query(ReferenceImage).all()
            logger.info(f"Found {len(ref_images)} reference images in database")

            for ref_img in ref_images:
                logger.debug(f"Loading CLIP features for: {ref_img.file_path}")
                features = self._extract_image_features(ref_img.file_path)
                if features is not None:
                    self.reference_features.append({
                        'features': features,
                        'category': ref_img.category,
                        'description': ref_img.description,
                        'id': ref_img.id
                    })

                    # Also extract text features if description exists
                    if ref_img.description:
                        text_features = self._extract_text_features(ref_img.description)
                        if text_features is not None:
                            self.reference_text_features.append({
                                'features': text_features,
                                'description': ref_img.description
                            })
                else:
                    logger.warning(f"Failed to extract CLIP features from {ref_img.file_path}")
        except Exception as e:
            logger.error(f"Failed to load reference images from database: {e}")

        # Load positive/negative examples from file system (legacy support)
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

    def get_classifier_stats(self) -> Dict:
        """Get classifier statistics (CLIP version)"""
        return {
            'reference_images': len(self.reference_features),
            'positive_examples': len(self.positive_examples),
            'negative_examples': len(self.negative_examples),
            'total_training_data': len(self.reference_features) + len(self.positive_examples) + len(self.negative_examples),
            'weights': self.preferences['scoring_weights'],
            'min_score_threshold': self.preferences['min_score'],
            'super_like_threshold': self.preferences['super_like_score'],
            'model_type': 'CLIP',
            'device': self.device
        }

    # Helper methods to match PreferenceManager interface
    def get_personality_traits(self) -> List[Dict]:
        """Get personality traits from preferences"""
        return self.preferences.get('personality_traits', [])

    def get_shared_interests(self) -> List[Dict]:
        """Get shared interests from preferences"""
        return self.preferences.get('shared_interests', [])


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
        """Initialize or reinitialize the classifier based on config"""
        try:
            # Close previous session if exists
            if self.db_session:
                self.db_session.close()

            # Create new session
            self.db_session = SessionLocal()

            # Choose classifier based on config
            model_type = settings.CLASSIFIER_MODEL.lower()

            if model_type == "clip":
                logger.info(f"🤖 Initializing CLIP classifier ({settings.CLIP_MODEL_NAME})")
                self.classifier = DatabaseAwareCLIPClassifier(
                    self.db_session,
                    model_name=settings.CLIP_MODEL_NAME
                )
                logger.info("✅ CLIP classifier initialized successfully")
            else:
                logger.info("🤖 Initializing ResNet50 classifier")
                self.classifier = DatabaseAwareClassifier(self.db_session)
                logger.info("✅ ResNet50 classifier initialized successfully")

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
