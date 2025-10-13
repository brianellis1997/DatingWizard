"""
CLIP-based Dating Classifier - Multimodal understanding with vision + language
Uses OpenAI's CLIP model for superior semantic understanding of dating profiles
"""

import numpy as np
import pytesseract
from PIL import Image
from typing import Dict, List, Optional
import torch
from transformers import CLIPProcessor, CLIPModel
from sklearn.metrics.pairwise import cosine_similarity
from loguru import logger
import os
import sys
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.analyzers.dating_classifier import ClassificationResult
from src.utils.preference_manager import PreferenceManager


class CLIPClassifier:
    """
    CLIP-based classifier for dating profiles

    Advantages over ResNet50:
    - Multimodal understanding (vision + language)
    - Better semantic matching ("athletic build", "artistic vibe")
    - Pre-trained on diverse internet images (better for faces)
    - Can understand text descriptions natively
    """

    def __init__(self, preferences_path: str = "config/preferences.json",
                 model_name: str = "openai/clip-vit-base-patch32"):
        """
        Initialize CLIP classifier

        Args:
            preferences_path: Path to preferences JSON file
            model_name: CLIP model variant (default: ViT-B/32, ~150MB)
                       Options:
                       - openai/clip-vit-base-patch32 (ViT-B/32) - Fastest, 150MB
                       - openai/clip-vit-base-patch16 (ViT-B/16) - Better quality, 350MB
                       - openai/clip-vit-large-patch14 (ViT-L/14) - Best quality, 900MB
        """
        logger.info(f"Initializing CLIPClassifier with {model_name}...")

        self.pref_manager = PreferenceManager(preferences_path)
        self.preferences = self.pref_manager.get_all_preferences()

        # Initialize CLIP model and processor
        try:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Using device: {self.device}")

            self.model = CLIPModel.from_pretrained(model_name).to(self.device)
            self.processor = CLIPProcessor.from_pretrained(model_name)
            self.model.eval()

            logger.info(f"✅ CLIP model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load CLIP model: {e}")
            raise

        # Load reference features
        self.reference_features = []
        self.reference_text_features = []  # Store text descriptions
        self.positive_examples = []
        self.negative_examples = []

        self._load_all_training_data()

        logger.info(f"Loaded {len(self.reference_features)} reference images")
        logger.info(f"Loaded {len(self.positive_examples)} positive examples")
        logger.info(f"Loaded {len(self.negative_examples)} negative examples")

    def _extract_image_features(self, image_path: str) -> Optional[np.ndarray]:
        """Extract CLIP image features from an image"""
        try:
            image = Image.open(image_path).convert('RGB')

            # Process image through CLIP
            inputs = self.processor(images=image, return_tensors="pt").to(self.device)

            with torch.no_grad():
                image_features = self.model.get_image_features(**inputs)
                # Normalize features for cosine similarity
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                features = image_features.squeeze().cpu().numpy()

            return features
        except Exception as e:
            logger.error(f"Failed to extract CLIP features from {image_path}: {e}")
            return None

    def _extract_text_features(self, text: str) -> Optional[np.ndarray]:
        """Extract CLIP text features from a description"""
        try:
            inputs = self.processor(text=[text], return_tensors="pt", padding=True).to(self.device)

            with torch.no_grad():
                text_features = self.model.get_text_features(**inputs)
                # Normalize features
                text_features = text_features / text_features.norm(dim=-1, keepdim=True)
                features = text_features.squeeze().cpu().numpy()

            return features
        except Exception as e:
            logger.error(f"Failed to extract CLIP text features: {e}")
            return None

    def _load_all_training_data(self):
        """Load all training data including reference images and examples"""
        # Load reference images
        try:
            reference_images = self.pref_manager.get_reference_images()
            for ref_img in reference_images:
                # Extract image features
                features = self._extract_image_features(ref_img['file_path'])
                if features is not None:
                    self.reference_features.append({
                        'features': features,
                        'category': ref_img['category'],
                        'description': ref_img['description'],
                        'id': ref_img['id']
                    })

                    # Also extract text features if description exists
                    if ref_img.get('description'):
                        text_features = self._extract_text_features(ref_img['description'])
                        if text_features is not None:
                            self.reference_text_features.append({
                                'features': text_features,
                                'description': ref_img['description']
                            })
        except Exception as e:
            logger.warning(f"Failed to load reference images: {e}")

        # Load positive examples
        liked_dir = "config/liked_profiles"
        if os.path.exists(liked_dir):
            for img_file in os.listdir(liked_dir):
                if img_file.endswith(('.jpg', '.png', '.jpeg')):
                    img_path = os.path.join(liked_dir, img_file)
                    features = self._extract_image_features(img_path)
                    if features is not None:
                        self.positive_examples.append(features)

        # Load negative examples
        disliked_dir = "config/disliked_profiles"
        if os.path.exists(disliked_dir):
            for img_file in os.listdir(disliked_dir):
                if img_file.endswith(('.jpg', '.png', '.jpeg')):
                    img_path = os.path.join(disliked_dir, img_file)
                    features = self._extract_image_features(img_path)
                    if features is not None:
                        self.negative_examples.append(features)

    def _calculate_physical_score(self, screenshot_features: np.ndarray) -> tuple[float, List[str]]:
        """
        Calculate physical attractiveness score using CLIP features

        Returns:
            Tuple of (score, reasons)
        """
        reasons = []

        if len(self.reference_features) == 0:
            logger.warning("No reference images loaded - using neutral physical score")
            return 0.5, ["No reference images for comparison"]

        # Calculate similarity to reference images
        reference_similarities = []
        for ref in self.reference_features:
            similarity = cosine_similarity(
                screenshot_features.reshape(1, -1),
                ref['features'].reshape(1, -1)
            )[0][0]
            reference_similarities.append(similarity)

        avg_ref_similarity = np.mean(reference_similarities)
        max_ref_similarity = np.max(reference_similarities)

        # Use max similarity as primary score, with avg as backup
        physical_score = 0.7 * max_ref_similarity + 0.3 * avg_ref_similarity

        # Add reasoning
        if max_ref_similarity > 0.75:
            reasons.append("Strong visual similarity to your reference images")
        elif max_ref_similarity > 0.6:
            reasons.append("Good visual similarity to your preferences")
        elif max_ref_similarity > 0.45:
            reasons.append("Moderate visual similarity to your preferences")
        else:
            reasons.append("Low visual similarity to your reference images")

        # Consider positive/negative examples if available
        if len(self.positive_examples) > 0:
            positive_similarities = [
                cosine_similarity(screenshot_features.reshape(1, -1), pos.reshape(1, -1))[0][0]
                for pos in self.positive_examples
            ]
            avg_positive = np.mean(positive_similarities)

            if avg_positive > 0.65:
                physical_score = physical_score * 0.6 + avg_positive * 0.4
                reasons.append("Similar to profiles you've liked before")

        if len(self.negative_examples) > 0:
            negative_similarities = [
                cosine_similarity(screenshot_features.reshape(1, -1), neg.reshape(1, -1))[0][0]
                for neg in self.negative_examples
            ]
            avg_negative = np.mean(negative_similarities)

            if avg_negative > 0.65:
                physical_score = physical_score * 0.7  # Reduce score
                reasons.append("Similar to profiles you've rejected")

        return float(np.clip(physical_score, 0, 1)), reasons

    def _extract_text_from_screenshot(self, screenshot_path: str) -> str:
        """Extract text from screenshot using OCR"""
        try:
            image = Image.open(screenshot_path)
            text = pytesseract.image_to_string(image)
            return text.strip()
        except Exception as e:
            logger.error(f"OCR failed for {screenshot_path}: {e}")
            return ""

    def _calculate_personality_score(self, bio_text: str, screenshot_features: np.ndarray) -> tuple[float, List[str]]:
        """
        Calculate personality compatibility using CLIP's text understanding

        This is where CLIP really shines - it can understand semantic meaning
        """
        reasons = []

        personality_traits = self.pref_manager.get_personality_traits()
        if not personality_traits:
            return 0.5, ["No personality preferences set"]

        # Combine traits into descriptive text for CLIP
        traits_text = ", ".join([trait['trait'] for trait in personality_traits])
        desired_personality = f"A person who is {traits_text}"

        # Extract text features for desired personality
        desired_features = self._extract_text_features(desired_personality)
        if desired_features is None:
            return 0.5, ["Failed to process personality preferences"]

        # If bio exists, use CLIP's text-text similarity
        if bio_text:
            bio_features = self._extract_text_features(bio_text)
            if bio_features is not None:
                text_similarity = cosine_similarity(
                    desired_features.reshape(1, -1),
                    bio_features.reshape(1, -1)
                )[0][0]

                if text_similarity > 0.6:
                    reasons.append(f"Bio aligns well with your personality preferences: {traits_text}")
                    return float(text_similarity), reasons
                elif text_similarity > 0.4:
                    reasons.append("Bio somewhat matches your personality preferences")
                    return float(text_similarity), reasons

        # No bio text - return neutral score
        # Don't penalize profiles without text, just give neutral 50%
        reasons.append("No bio text to analyze personality match")
        return 0.5, reasons

    def _calculate_interest_score(self, bio_text: str) -> tuple[float, List[str]]:
        """Calculate shared interests score"""
        reasons = []

        shared_interests = self.pref_manager.get_shared_interests()
        if not shared_interests:
            return 0.5, ["No interest preferences set"]

        if not bio_text:
            return 0.5, ["No bio text to analyze"]

        # Check for keyword matches (simple approach)
        bio_lower = bio_text.lower()
        matched_interests = []
        dealbreaker_violated = False

        for interest in shared_interests:
            interest_text = interest['interest'].lower()
            if interest_text in bio_lower:
                matched_interests.append(interest['interest'])
                if interest['is_dealbreaker']:
                    dealbreaker_violated = True

        if len(matched_interests) > 0:
            interest_score = min(len(matched_interests) / len(shared_interests), 1.0)
            reasons.append(f"Shares interests: {', '.join(matched_interests)}")
        else:
            interest_score = 0.3
            reasons.append("No obvious shared interests mentioned")

        return float(interest_score), reasons

    def classify_screenshot(self, screenshot_path: str,
                          min_threshold: Optional[float] = None) -> ClassificationResult:
        """
        Main classification method using CLIP

        Args:
            screenshot_path: Path to screenshot image
            min_threshold: Minimum score threshold for match (uses preferences if None)
        """
        result = ClassificationResult()
        result.metadata['screenshot_path'] = screenshot_path

        # Extract image features using CLIP
        screenshot_features = self._extract_image_features(screenshot_path)
        if screenshot_features is None:
            logger.error(f"Failed to extract features from {screenshot_path}")
            return result

        # Extract text from screenshot
        extracted_text = self._extract_text_from_screenshot(screenshot_path)
        result.extracted_data['bio'] = extracted_text

        # Calculate component scores
        physical_score, physical_reasons = self._calculate_physical_score(screenshot_features)
        personality_score, personality_reasons = self._calculate_personality_score(
            extracted_text, screenshot_features
        )
        interest_score, interest_reasons = self._calculate_interest_score(extracted_text)

        result.component_scores['physical'] = physical_score
        result.component_scores['personality'] = personality_score
        result.component_scores['interests'] = interest_score

        # Get weights from preferences
        result.weights = self.preferences['scoring_weights']

        # Calculate weighted confidence score
        result.confidence_score = (
            physical_score * result.weights['physical'] +
            personality_score * result.weights['personality'] +
            interest_score * result.weights['interests']
        )

        # Determine if match
        threshold = min_threshold if min_threshold is not None else self.preferences['min_score']
        result.is_match = result.confidence_score >= threshold

        # Compile reasons
        result.reasons = physical_reasons + personality_reasons + interest_reasons

        if result.is_match:
            result.reasons.insert(0, "Strong overall compatibility")
        else:
            result.reasons.insert(0, f"Score {result.confidence_score:.1%} below threshold {threshold:.1%}")

        return result

    def classify_batch(self, screenshot_paths: List[str]) -> List[ClassificationResult]:
        """Classify multiple screenshots"""
        results = []
        for path in screenshot_paths:
            result = self.classify_screenshot(path)
            results.append(result)
        return results

    def get_stats(self) -> Dict:
        """Get classifier statistics"""
        return {
            'reference_images': len(self.reference_features),
            'positive_examples': len(self.positive_examples),
            'negative_examples': len(self.negative_examples),
            'total_training_data': len(self.reference_features) + len(self.positive_examples) + len(self.negative_examples),
            'weights': self.preferences['scoring_weights'],
            'min_score_threshold': self.preferences['min_score'],
            'super_like_threshold': self.preferences['super_like_score'],
            'model_type': 'CLIP (ViT-B/32)',
            'device': self.device
        }
