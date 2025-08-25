"""
Profile Analyzer - Analyzes profiles based on user preferences
Uses computer vision and NLP to make swipe decisions
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


class ProfileAnalyzer:
    """Analyzes profiles to make swipe decisions"""
    
    def __init__(self, preferences_path: str = "config/preferences.json"):
        self.preferences = self._load_preferences(preferences_path)
        self.image_model = self._initialize_image_model()
        self.transform = self._get_image_transform()
        self.positive_examples = []
        self.negative_examples = []
        self._load_training_examples()
        
    def _load_preferences(self, path: str) -> Dict:
        """Load user preferences from JSON file"""
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
        else:
            # Default preferences
            return {
                "age_range": {"min": 25, "max": 35},
                "bio_keywords": {
                    "positive": ["fitness", "travel", "foodie", "adventure", "professional"],
                    "negative": ["drama", "games", "hookup", "sugar", "venmo"],
                    "required": []
                },
                "interests": {
                    "preferred": ["hiking", "yoga", "reading", "cooking"],
                    "dealbreakers": []
                },
                "swipe_threshold": 0.6,
                "super_like_threshold": 0.85
            }
            
    def _initialize_image_model(self):
        """Initialize pre-trained ResNet model for image feature extraction"""
        model = models.resnet50(pretrained=True)
        # Remove the final classification layer
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
        
    def _load_training_examples(self):
        """Load positive and negative example profiles"""
        # Load liked profiles
        liked_dir = "config/liked_profiles"
        if os.path.exists(liked_dir):
            for img_file in os.listdir(liked_dir):
                if img_file.endswith(('.jpg', '.png')):
                    img_path = os.path.join(liked_dir, img_file)
                    features = self._extract_image_features(img_path)
                    if features is not None:
                        self.positive_examples.append(features)
                        
        # Load disliked profiles
        disliked_dir = "config/disliked_profiles"
        if os.path.exists(disliked_dir):
            for img_file in os.listdir(disliked_dir):
                if img_file.endswith(('.jpg', '.png')):
                    img_path = os.path.join(disliked_dir, img_file)
                    features = self._extract_image_features(img_path)
                    if features is not None:
                        self.negative_examples.append(features)
                        
        logger.info(f"Loaded {len(self.positive_examples)} positive and {len(self.negative_examples)} negative examples")
        
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
            
    def analyze_screenshot(self, screenshot_path: str) -> Dict:
        """Analyze a screenshot to make swipe decision"""
        logger.info(f"Analyzing screenshot: {screenshot_path}")
        
        # Extract bio text
        bio_text = self._extract_bio_text(screenshot_path)
        bio_score = self._analyze_bio(bio_text)
        
        # Extract and analyze profile images
        image_score = self._analyze_profile_image(screenshot_path)
        
        # Combined score
        final_score = (bio_score * 0.4) + (image_score * 0.6)
        
        # Determine decision
        if final_score >= self.preferences['super_like_threshold']:
            decision = 'super_like'
        elif final_score >= self.preferences['swipe_threshold']:
            decision = 'right'
        else:
            decision = 'left'
            
        result = {
            'decision': decision,
            'confidence': final_score,
            'bio_score': bio_score,
            'image_score': image_score,
            'bio_text': bio_text[:200] if bio_text else None,
            'reasons': self._generate_reasons(bio_score, image_score, bio_text)
        }
        
        logger.info(f"Decision: {decision} (confidence: {final_score:.2f})")
        return result
        
    def _extract_bio_text(self, screenshot_path: str) -> str:
        """Extract bio text from screenshot using OCR"""
        try:
            # Read image
            image = cv2.imread(screenshot_path)
            
            # Define approximate bio region (adjust based on actual layout)
            height, width = image.shape[:2]
            bio_region = image[int(height*0.4):int(height*0.8), int(width*0.1):int(width*0.9)]
            
            # Preprocess for better OCR
            gray = cv2.cvtColor(bio_region, cv2.COLOR_BGR2GRAY)
            thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
            
            # Extract text
            text = pytesseract.image_to_string(thresh)
            
            # Clean up text
            text = ' '.join(text.split())
            
            return text
            
        except Exception as e:
            logger.error(f"Failed to extract bio text: {e}")
            return ""
            
    def _analyze_bio(self, bio_text: str) -> float:
        """Analyze bio text and return score"""
        if not bio_text:
            return 0.5  # Neutral score if no bio
            
        bio_lower = bio_text.lower()
        score = 0.5  # Start with neutral
        
        # Check for red flags (immediate disqualification)
        for keyword in self.preferences['bio_keywords']['negative']:
            if keyword.lower() in bio_lower:
                logger.debug(f"Found negative keyword: {keyword}")
                return 0.0
                
        # Check required keywords
        required = self.preferences['bio_keywords'].get('required', [])
        if required:
            has_required = any(kw.lower() in bio_lower for kw in required)
            if not has_required:
                return 0.2  # Low score if missing required keywords
                
        # Check positive keywords
        for keyword in self.preferences['bio_keywords']['positive']:
            if keyword.lower() in bio_lower:
                score += 0.1
                logger.debug(f"Found positive keyword: {keyword}")
                
        # Check interests
        for interest in self.preferences['interests']['preferred']:
            if interest.lower() in bio_lower:
                score += 0.05
                
        # Cap at 1.0
        return min(score, 1.0)
        
    def _analyze_profile_image(self, screenshot_path: str) -> float:
        """Analyze profile image and return similarity score"""
        try:
            # Extract features from screenshot
            features = self._extract_image_features(screenshot_path)
            
            if features is None:
                return 0.5  # Neutral score if can't extract features
                
            # If we have training examples, compare
            if self.positive_examples:
                # Calculate similarity to positive examples
                pos_similarities = []
                for pos_example in self.positive_examples:
                    sim = cosine_similarity(
                        features.reshape(1, -1),
                        pos_example.reshape(1, -1)
                    )[0][0]
                    pos_similarities.append(sim)
                    
                avg_pos_similarity = np.mean(pos_similarities)
                
                # Calculate similarity to negative examples (if any)
                avg_neg_similarity = 0.5
                if self.negative_examples:
                    neg_similarities = []
                    for neg_example in self.negative_examples:
                        sim = cosine_similarity(
                            features.reshape(1, -1),
                            neg_example.reshape(1, -1)
                        )[0][0]
                        neg_similarities.append(sim)
                    avg_neg_similarity = np.mean(neg_similarities)
                    
                # Score based on relative similarity
                score = (avg_pos_similarity - avg_neg_similarity + 1) / 2
                return max(0, min(1, score))
                
            else:
                # No training examples, return neutral
                return 0.5
                
        except Exception as e:
            logger.error(f"Failed to analyze profile image: {e}")
            return 0.5
            
    def _generate_reasons(self, bio_score: float, image_score: float, bio_text: str) -> List[str]:
        """Generate human-readable reasons for the decision"""
        reasons = []
        
        if bio_score > 0.7:
            reasons.append("Bio contains interesting keywords")
        elif bio_score < 0.3:
            reasons.append("Bio lacks appealing content")
            
        if image_score > 0.7:
            reasons.append("Photos match your preferences")
        elif image_score < 0.3:
            reasons.append("Photos don't match typical preferences")
            
        # Check for specific interests
        if bio_text:
            bio_lower = bio_text.lower()
            for interest in self.preferences['interests']['preferred']:
                if interest.lower() in bio_lower:
                    reasons.append(f"Shares interest: {interest}")
                    
        return reasons
        
    def update_preferences(self, new_preferences: Dict):
        """Update user preferences"""
        self.preferences.update(new_preferences)
        # Save to file
        with open("config/preferences.json", 'w') as f:
            json.dump(self.preferences, f, indent=2)
        logger.info("Preferences updated")
        
    def add_training_example(self, image_path: str, liked: bool):
        """Add a new training example"""
        features = self._extract_image_features(image_path)
        if features is not None:
            if liked:
                self.positive_examples.append(features)
                # Save to liked folder
                os.makedirs("config/liked_profiles", exist_ok=True)
                filename = os.path.basename(image_path)
                Image.open(image_path).save(f"config/liked_profiles/{filename}")
            else:
                self.negative_examples.append(features)
                # Save to disliked folder
                os.makedirs("config/disliked_profiles", exist_ok=True)
                filename = os.path.basename(image_path)
                Image.open(image_path).save(f"config/disliked_profiles/{filename}")
                
            logger.info(f"Added training example: {'liked' if liked else 'disliked'}")