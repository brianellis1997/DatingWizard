"""
Classifier Service - Wraps the DatingClassifier for API use
"""

import sys
import os
from pathlib import Path
from typing import Dict, List
from PIL import Image

# Add src to path to import existing classifier
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.analyzers.dating_classifier import DatingClassifier, ClassificationResult as CLIClassificationResult
from backend.config import settings
from loguru import logger


class ClassifierService:
    """Service for managing the DatingClassifier"""

    def __init__(self):
        """Initialize the classifier"""
        self.classifier = None
        self._init_classifier()

    def _init_classifier(self):
        """Initialize or reinitialize the classifier"""
        try:
            self.classifier = DatingClassifier(settings.PREFERENCES_PATH)
            logger.info("Classifier initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize classifier: {e}")
            raise

    def reload_classifier(self):
        """Reload the classifier (useful after preference updates)"""
        self._init_classifier()

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
