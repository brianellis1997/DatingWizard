"""
Dating Classifier - Unified multimodal classification system
Analyzes profile screenshots to determine match compatibility
"""

import cv2
import numpy as np
import pytesseract
from PIL import Image
from typing import Dict, List, Tuple, Optional
import torch
import torchvision.transforms as transforms
from torchvision import models
from sklearn.metrics.pairwise import cosine_similarity
import re
from loguru import logger
import json
import os
import sys
from pathlib import Path
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.utils.preference_manager import PreferenceManager


class ClassificationResult:
    """Result object for profile classification"""

    def __init__(self):
        self.is_match = False
        self.confidence_score = 0.0
        self.component_scores = {
            'physical': 0.0,
            'personality': 0.0,
            'interests': 0.0
        }
        self.weights = {
            'physical': 0.6,
            'personality': 0.3,
            'interests': 0.1
        }
        self.reasons = []
        self.extracted_data = {
            'name': None,
            'age': None,
            'bio': None,
            'images_found': 0
        }
        self.metadata = {
            'timestamp': datetime.now().isoformat(),
            'screenshot_path': None
        }

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'is_match': self.is_match,
            'confidence_score': self.confidence_score,
            'component_scores': self.component_scores,
            'weights': self.weights,
            'reasons': self.reasons,
            'extracted_data': self.extracted_data,
            'metadata': self.metadata
        }

    def __str__(self) -> str:
        """Human-readable string representation"""
        match_str = "✅ MATCH" if self.is_match else "❌ NO MATCH"
        lines = [
            f"\n{'='*60}",
            f"{match_str} (Confidence: {self.confidence_score:.1%})",
            f"{'='*60}",
            f"\n📊 Component Scores:",
            f"  • Physical:    {self.component_scores['physical']:.1%} (weight: {self.weights['physical']:.1%})",
            f"  • Personality: {self.component_scores['personality']:.1%} (weight: {self.weights['personality']:.1%})",
            f"  • Interests:   {self.component_scores['interests']:.1%} (weight: {self.weights['interests']:.1%})",
            f"\n📝 Extracted Data:",
        ]

        if self.extracted_data['name']:
            lines.append(f"  • Name: {self.extracted_data['name']}")
        if self.extracted_data['age']:
            lines.append(f"  • Age: {self.extracted_data['age']}")
        if self.extracted_data['bio']:
            bio_preview = self.extracted_data['bio'][:100] + "..." if len(self.extracted_data['bio']) > 100 else self.extracted_data['bio']
            lines.append(f"  • Bio: {bio_preview}")

        lines.append(f"\n💡 Reasons:")
        for reason in self.reasons:
            lines.append(f"  • {reason}")

        lines.append(f"{'='*60}\n")
        return '\n'.join(lines)


class DatingClassifier:
    """
    Unified dating profile classifier using multimodal analysis
    Combines image similarity, text analysis, and user preferences
    """

    def __init__(self, preferences_path: str = "config/preferences.json"):
        logger.info("Initializing DatingClassifier...")

        self.pref_manager = PreferenceManager(preferences_path)
        self.preferences = self.pref_manager.get_all_preferences()

        # Initialize image analysis
        self.image_model = self._initialize_image_model()
        self.transform = self._get_image_transform()

        # Load reference features
        self.reference_features = []
        self.positive_examples = []
        self.negative_examples = []

        self._load_all_training_data()

        logger.info(f"Loaded {len(self.reference_features)} reference images")
        logger.info(f"Loaded {len(self.positive_examples)} positive examples")
        logger.info(f"Loaded {len(self.negative_examples)} negative examples")

    def _initialize_image_model(self):
        """Initialize pre-trained ResNet model for image feature extraction"""
        model = models.resnet50(pretrained=True)
        model = torch.nn.Sequential(*list(model.children())[:-1])
        model.eval()
        return model

    def _get_image_transform(self):
        """Get image transformation pipeline"""
        return transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                               std=[0.229, 0.224, 0.225])
        ])

    def _load_all_training_data(self):
        """Load all training data including reference images and examples"""
        # Load reference images (highest priority)
        try:
            reference_images = self.pref_manager.get_reference_images()
            for ref_img in reference_images:
                features = self._extract_image_features(ref_img['file_path'])
                if features is not None:
                    self.reference_features.append({
                        'features': features,
                        'category': ref_img['category'],
                        'description': ref_img['description'],
                        'id': ref_img['id']
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

    def _extract_image_features(self, image_path: str) -> Optional[np.ndarray]:
        """Extract feature vector from image using ResNet"""
        try:
            image = Image.open(image_path).convert('RGB')
            image_tensor = self.transform(image).unsqueeze(0)

            with torch.no_grad():
                features = self.image_model(image_tensor)
                features = features.squeeze().numpy()

            return features
        except Exception as e:
            logger.error(f"Failed to extract features from {image_path}: {e}")
            return None

    def classify_screenshot(self, screenshot_path: str,
                          min_threshold: Optional[float] = None) -> ClassificationResult:
        """
        Main classification method - analyzes a profile screenshot

        Args:
            screenshot_path: Path to screenshot image
            min_threshold: Optional custom threshold (uses preferences default if None)

        Returns:
            ClassificationResult object with detailed analysis
        """
        logger.info(f"Classifying screenshot: {screenshot_path}")
        result = ClassificationResult()
        result.metadata['screenshot_path'] = screenshot_path

        # Extract data from screenshot
        extracted_data = self._extract_profile_data(screenshot_path)
        result.extracted_data = extracted_data

        # Get weights from preferences
        if 'partner_preferences' in self.preferences:
            result.weights['physical'] = self.preferences['partner_preferences']['physical']['importance_weight']
            result.weights['personality'] = self.preferences['partner_preferences']['personality']['importance_weight']
            result.weights['interests'] = self.preferences['partner_preferences']['interests']['importance_weight']

        # Analyze physical match (image-based)
        physical_score = self._analyze_physical_match(screenshot_path)
        result.component_scores['physical'] = physical_score

        # Analyze personality match (bio-based)
        personality_score = self._analyze_personality_match(extracted_data.get('bio', ''))
        result.component_scores['personality'] = personality_score

        # Analyze interest match
        interest_score = self._analyze_interest_match(extracted_data.get('bio', ''))
        result.component_scores['interests'] = interest_score

        # Calculate weighted final score
        result.confidence_score = (
            physical_score * result.weights['physical'] +
            personality_score * result.weights['personality'] +
            interest_score * result.weights['interests']
        )

        # Determine if match
        threshold = min_threshold or self.preferences.get('matching_criteria', {}).get('minimum_score', 0.6)
        result.is_match = result.confidence_score >= threshold

        # Generate reasons
        result.reasons = self._generate_reasons(result, extracted_data)

        logger.info(f"Classification complete: {'MATCH' if result.is_match else 'NO MATCH'} ({result.confidence_score:.2%})")
        return result

    def _extract_profile_data(self, screenshot_path: str) -> Dict:
        """Extract structured data from screenshot"""
        data = {
            'name': None,
            'age': None,
            'bio': '',
            'images_found': 0
        }

        try:
            # Read image
            img = cv2.imread(screenshot_path)
            if img is None:
                logger.error(f"Failed to read screenshot: {screenshot_path}")
                return data

            height, width = img.shape[:2]

            # Extract text using OCR from different regions
            full_text = self._extract_text_from_image(img)
            data['bio'] = full_text

            # Try to extract name and age using patterns
            name_age_match = re.search(r'^([A-Za-z\s]+),?\s*(\d{2})', full_text, re.MULTILINE)
            if name_age_match:
                data['name'] = name_age_match.group(1).strip()
                data['age'] = int(name_age_match.group(2))

            # Count image regions (simplified)
            data['images_found'] = 1

        except Exception as e:
            logger.error(f"Error extracting profile data: {e}")

        return data

    def _extract_text_from_image(self, img: np.ndarray) -> str:
        """Extract text from image using OCR"""
        try:
            # Preprocess image for better OCR
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Apply threshold to get better text extraction
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

            # Extract text
            text = pytesseract.image_to_string(thresh)

            # Clean up text
            text = ' '.join(text.split())

            return text
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return ""

    def _analyze_physical_match(self, screenshot_path: str) -> float:
        """Analyze physical compatibility using image similarity"""
        try:
            # Extract features from screenshot
            features = self._extract_image_features(screenshot_path)

            if features is None:
                logger.warning("Could not extract features from screenshot")
                return 0.5

            scores = []
            weights = []

            # Method 1: Compare to reference images (highest priority)
            if self.reference_features:
                ref_similarities = []
                for ref_data in self.reference_features:
                    sim = cosine_similarity(
                        features.reshape(1, -1),
                        ref_data['features'].reshape(1, -1)
                    )[0][0]
                    ref_similarities.append(sim)

                avg_ref_sim = np.mean(ref_similarities)
                max_ref_sim = np.max(ref_similarities)

                # Use average with bonus for strong matches
                ref_score = (avg_ref_sim * 0.6) + (max_ref_sim * 0.4)
                scores.append(ref_score)
                weights.append(0.7)

                logger.debug(f"Reference similarity: avg={avg_ref_sim:.3f}, max={max_ref_sim:.3f}, score={ref_score:.3f}")

            # Method 2: Compare to positive/negative examples
            if self.positive_examples:
                pos_similarities = [
                    cosine_similarity(features.reshape(1, -1), pos.reshape(1, -1))[0][0]
                    for pos in self.positive_examples
                ]
                avg_pos_sim = np.mean(pos_similarities)

                if self.negative_examples:
                    neg_similarities = [
                        cosine_similarity(features.reshape(1, -1), neg.reshape(1, -1))[0][0]
                        for neg in self.negative_examples
                    ]
                    avg_neg_sim = np.mean(neg_similarities)

                    # Relative scoring
                    training_score = (avg_pos_sim - avg_neg_sim + 1) / 2
                else:
                    training_score = avg_pos_sim

                scores.append(training_score)
                weights.append(0.3)

                logger.debug(f"Training similarity: {training_score:.3f}")

            # Calculate weighted average
            if scores:
                total_weight = sum(weights)
                final_score = sum(s * w for s, w in zip(scores, weights)) / total_weight
                return max(0.0, min(1.0, final_score))
            else:
                logger.warning("No training data available for physical analysis")
                return 0.5

        except Exception as e:
            logger.error(f"Physical analysis failed: {e}")
            return 0.5

    def _analyze_personality_match(self, bio_text: str) -> float:
        """Analyze personality compatibility from bio text"""
        if not bio_text:
            return 0.5

        bio_lower = bio_text.lower()
        score = 0.5

        # Check for negative keywords (dealbreakers)
        negative_keywords = self.preferences.get('bio_keywords', {}).get('negative', [])
        for keyword in negative_keywords:
            if keyword.lower() in bio_lower:
                logger.debug(f"Found dealbreaker keyword: {keyword}")
                return 0.0

        # Check for positive personality traits
        if 'partner_preferences' in self.preferences:
            traits = self.preferences['partner_preferences']['personality'].get('traits', [])
            matches = 0
            for trait in traits:
                if trait.lower() in bio_lower:
                    matches += 1
                    score += 0.15
                    logger.debug(f"Found desired trait: {trait}")

            if traits:
                logger.debug(f"Matched {matches}/{len(traits)} personality traits")

        # Check for positive keywords
        positive_keywords = self.preferences.get('bio_keywords', {}).get('positive', [])
        for keyword in positive_keywords:
            if keyword.lower() in bio_lower:
                score += 0.08
                logger.debug(f"Found positive keyword: {keyword}")

        return min(1.0, score)

    def _analyze_interest_match(self, bio_text: str) -> float:
        """Analyze interest compatibility"""
        if not bio_text:
            return 0.5

        bio_lower = bio_text.lower()
        score = 0.5

        if 'partner_preferences' in self.preferences:
            interests_pref = self.preferences['partner_preferences']['interests']

            # Check for dealbreaker interests
            dealbreakers = interests_pref.get('dealbreaker_interests', [])
            for dealbreaker in dealbreakers:
                if dealbreaker.lower() in bio_lower:
                    logger.debug(f"Found dealbreaker interest: {dealbreaker}")
                    return 0.0

            # Check for shared interests
            shared_interests = interests_pref.get('shared_interests', [])
            matches = 0
            for interest in shared_interests:
                if interest.lower() in bio_lower:
                    matches += 1
                    score += 0.15
                    logger.debug(f"Found shared interest: {interest}")

            if shared_interests:
                logger.debug(f"Matched {matches}/{len(shared_interests)} shared interests")

        return min(1.0, score)

    def _generate_reasons(self, result: ClassificationResult, extracted_data: Dict) -> List[str]:
        """Generate human-readable reasons for the classification"""
        reasons = []

        # Physical reasons
        physical_score = result.component_scores['physical']
        if physical_score >= 0.75:
            if self.reference_features:
                reasons.append("Strong visual similarity to your reference images")
            elif self.positive_examples:
                reasons.append("Photos match your learned preferences well")
        elif physical_score <= 0.35:
            reasons.append("Photos don't align with your visual preferences")
        elif 0.5 <= physical_score < 0.75:
            reasons.append("Moderate visual compatibility")

        # Personality reasons
        personality_score = result.component_scores['personality']
        if personality_score >= 0.75:
            reasons.append("Bio shows strong personality compatibility")
        elif personality_score <= 0.35:
            reasons.append("Bio lacks appealing personality indicators")

        # Interest reasons
        interest_score = result.component_scores['interests']
        if interest_score >= 0.75:
            reasons.append("Excellent interest alignment")
        elif interest_score <= 0.35:
            reasons.append("Limited shared interests found")

        # Specific interest mentions
        bio_text = extracted_data.get('bio', '')
        if bio_text and 'partner_preferences' in self.preferences:
            shared_interests = self.preferences['partner_preferences']['interests'].get('shared_interests', [])
            bio_lower = bio_text.lower()

            found_interests = [i for i in shared_interests if i.lower() in bio_lower]
            if found_interests:
                if len(found_interests) <= 3:
                    for interest in found_interests:
                        reasons.append(f"Shares your interest in {interest}")
                else:
                    reasons.append(f"Shares {len(found_interests)} of your interests: {', '.join(found_interests[:3])}")

        # Age check
        if extracted_data.get('age'):
            age_range = self.preferences.get('age_range', {})
            min_age = age_range.get('min', 18)
            max_age = age_range.get('max', 99)

            age = extracted_data['age']
            if min_age <= age <= max_age:
                reasons.append(f"Age {age} is within your preferred range ({min_age}-{max_age})")
            else:
                reasons.append(f"Age {age} is outside your preferred range ({min_age}-{max_age})")

        # Overall confidence
        if result.confidence_score >= 0.85:
            reasons.insert(0, "🌟 Exceptional match across all criteria")
        elif result.confidence_score >= 0.70:
            reasons.insert(0, "Strong overall compatibility")

        return reasons if reasons else ["Neutral compatibility - no strong signals either way"]

    def batch_classify(self, screenshot_paths: List[str]) -> List[ClassificationResult]:
        """Classify multiple screenshots"""
        results = []
        for path in screenshot_paths:
            try:
                result = self.classify_screenshot(path)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to classify {path}: {e}")

        return results

    def get_classifier_stats(self) -> Dict:
        """Get statistics about the classifier's training data"""
        return {
            'reference_images': len(self.reference_features),
            'positive_examples': len(self.positive_examples),
            'negative_examples': len(self.negative_examples),
            'total_training_data': len(self.reference_features) + len(self.positive_examples) + len(self.negative_examples),
            'weights': {
                'physical': self.preferences.get('partner_preferences', {}).get('physical', {}).get('importance_weight', 0.6),
                'personality': self.preferences.get('partner_preferences', {}).get('personality', {}).get('importance_weight', 0.3),
                'interests': self.preferences.get('partner_preferences', {}).get('interests', {}).get('importance_weight', 0.1)
            },
            'min_score_threshold': self.preferences.get('matching_criteria', {}).get('minimum_score', 0.6),
            'super_like_threshold': self.preferences.get('matching_criteria', {}).get('super_like_score', 0.85)
        }
