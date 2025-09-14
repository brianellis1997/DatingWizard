"""
Preference Manager - Handles user preference input and management
Allows users to upload reference images and detailed descriptions of ideal partners
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from PIL import Image
import uuid
from loguru import logger
import hashlib


class PreferenceManager:
    """Manages user preferences for AI partner matching"""
    
    def __init__(self, config_path: str = "config/preferences.json"):
        self.config_path = config_path
        self.preferences = self._load_preferences()
        self.reference_images_dir = Path("config/reference_images")
        self.reference_images_dir.mkdir(exist_ok=True)
        
    def _load_preferences(self) -> Dict:
        """Load existing preferences or create default"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return self._get_default_preferences()
        
    def _get_default_preferences(self) -> Dict:
        """Get default preference structure"""
        return {
            "version": "2.0",
            "partner_preferences": {
                "physical": {
                    "reference_images": [],
                    "importance_weight": 0.6,
                    "features": {
                        "face_type": "",
                        "body_type": "",
                        "height_preference": "",
                        "style_preference": ""
                    }
                },
                "personality": {
                    "traits": [],
                    "importance_weight": 0.3,
                    "communication_style": "",
                    "lifestyle_compatibility": []
                },
                "interests": {
                    "shared_interests": [],
                    "importance_weight": 0.1,
                    "dealbreaker_interests": []
                }
            },
            "matching_criteria": {
                "minimum_score": 0.6,
                "super_like_score": 0.85,
                "diversity_factor": 0.2,
                "recency_weight": 0.1
            },
            # Keep existing structure for backward compatibility
            "age_range": {"min": 25, "max": 35},
            "bio_keywords": {
                "positive": [],
                "negative": [],
                "required": []
            },
            "automation": {
                "swipe_threshold": 0.6,
                "super_like_threshold": 0.85,
                "max_swipes_per_hour": 100,
                "min_delay_seconds": 2,
                "max_delay_seconds": 5
            }
        }
        
    def add_reference_image(self, image_path: str, category: str = "general", 
                           description: str = "") -> str:
        """Add a reference image of ideal partner type"""
        try:
            # Validate image
            with Image.open(image_path) as img:
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Generate unique filename
                image_hash = self._get_image_hash(image_path)
                filename = f"{category}_{image_hash}.jpg"
                dest_path = self.reference_images_dir / filename
                
                # Save image
                img.save(dest_path, "JPEG", quality=90)
                
                # Add to preferences
                reference_data = {
                    "id": str(uuid.uuid4()),
                    "filename": filename,
                    "category": category,
                    "description": description,
                    "added_date": str(Path(image_path).stat().st_mtime),
                    "file_path": str(dest_path)
                }
                
                self.preferences["partner_preferences"]["physical"]["reference_images"].append(reference_data)
                self._save_preferences()
                
                logger.info(f"Added reference image: {filename}")
                return reference_data["id"]
                
        except Exception as e:
            logger.error(f"Failed to add reference image: {e}")
            raise
            
    def remove_reference_image(self, image_id: str) -> bool:
        """Remove a reference image"""
        try:
            references = self.preferences["partner_preferences"]["physical"]["reference_images"]
            for i, ref in enumerate(references):
                if ref["id"] == image_id:
                    # Remove file
                    file_path = Path(ref["file_path"])
                    if file_path.exists():
                        file_path.unlink()
                    
                    # Remove from preferences
                    references.pop(i)
                    self._save_preferences()
                    
                    logger.info(f"Removed reference image: {image_id}")
                    return True
            return False
        except Exception as e:
            logger.error(f"Failed to remove reference image: {e}")
            return False
            
    def update_physical_preferences(self, **kwargs) -> None:
        """Update physical preference details"""
        physical_prefs = self.preferences["partner_preferences"]["physical"]
        
        for key, value in kwargs.items():
            if key in ["importance_weight"]:
                physical_prefs[key] = value
            elif key in physical_prefs["features"]:
                physical_prefs["features"][key] = value
                
        self._save_preferences()
        logger.info("Updated physical preferences")
        
    def update_personality_preferences(self, traits: List[str] = None, 
                                     communication_style: str = None,
                                     lifestyle_compatibility: List[str] = None,
                                     importance_weight: float = None) -> None:
        """Update personality preferences"""
        personality_prefs = self.preferences["partner_preferences"]["personality"]
        
        if traits is not None:
            personality_prefs["traits"] = traits
        if communication_style is not None:
            personality_prefs["communication_style"] = communication_style
        if lifestyle_compatibility is not None:
            personality_prefs["lifestyle_compatibility"] = lifestyle_compatibility
        if importance_weight is not None:
            personality_prefs["importance_weight"] = importance_weight
            
        self._save_preferences()
        logger.info("Updated personality preferences")
        
    def update_interest_preferences(self, shared_interests: List[str] = None,
                                  dealbreaker_interests: List[str] = None,
                                  importance_weight: float = None) -> None:
        """Update interest preferences"""
        interest_prefs = self.preferences["partner_preferences"]["interests"]
        
        if shared_interests is not None:
            interest_prefs["shared_interests"] = shared_interests
        if dealbreaker_interests is not None:
            interest_prefs["dealbreaker_interests"] = dealbreaker_interests
        if importance_weight is not None:
            interest_prefs["importance_weight"] = importance_weight
            
        self._save_preferences()
        logger.info("Updated interest preferences")
        
    def update_matching_criteria(self, **kwargs) -> None:
        """Update matching criteria settings"""
        criteria = self.preferences["matching_criteria"]
        
        for key, value in kwargs.items():
            if key in criteria:
                criteria[key] = value
                
        self._save_preferences()
        logger.info("Updated matching criteria")
        
    def get_reference_images(self, category: str = None) -> List[Dict]:
        """Get reference images, optionally filtered by category"""
        references = self.preferences["partner_preferences"]["physical"]["reference_images"]
        
        if category:
            return [ref for ref in references if ref["category"] == category]
        return references
        
    def get_all_preferences(self) -> Dict:
        """Get complete preferences dictionary"""
        return self.preferences.copy()
        
    def export_preferences(self, export_path: str) -> None:
        """Export preferences to a file"""
        with open(export_path, 'w') as f:
            json.dump(self.preferences, f, indent=2)
        logger.info(f"Exported preferences to {export_path}")
        
    def import_preferences(self, import_path: str, merge: bool = True) -> None:
        """Import preferences from a file"""
        with open(import_path, 'r') as f:
            imported_prefs = json.load(f)
            
        if merge:
            # Merge with existing preferences
            self._deep_merge(self.preferences, imported_prefs)
        else:
            # Replace preferences entirely
            self.preferences = imported_prefs
            
        self._save_preferences()
        logger.info(f"Imported preferences from {import_path}")
        
    def get_preference_summary(self) -> Dict:
        """Get a summary of current preferences"""
        physical = self.preferences["partner_preferences"]["physical"]
        personality = self.preferences["partner_preferences"]["personality"]
        interests = self.preferences["partner_preferences"]["interests"]
        
        return {
            "reference_images_count": len(physical["reference_images"]),
            "physical_weight": physical["importance_weight"],
            "personality_traits": personality["traits"],
            "personality_weight": personality["importance_weight"],
            "shared_interests": interests["shared_interests"],
            "interest_weight": interests["importance_weight"],
            "minimum_score": self.preferences["matching_criteria"]["minimum_score"]
        }
        
    def _get_image_hash(self, image_path: str) -> str:
        """Generate hash for image deduplication"""
        with open(image_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()[:8]
            
    def _save_preferences(self) -> None:
        """Save preferences to file"""
        # Ensure directory exists
        config_dir = os.path.dirname(self.config_path)
        if config_dir:  # Only create directory if there is one
            os.makedirs(config_dir, exist_ok=True)
        
        with open(self.config_path, 'w') as f:
            json.dump(self.preferences, f, indent=2)
            
    def _deep_merge(self, base_dict: Dict, merge_dict: Dict) -> None:
        """Deep merge two dictionaries"""
        for key, value in merge_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_merge(base_dict[key], value)
            else:
                base_dict[key] = value