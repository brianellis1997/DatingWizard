#!/usr/bin/env python3
"""
Preference Migration Script - Upgrades old preferences.json to new schema
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path


def migrate_preferences(config_path: str = "config/preferences.json"):
    """Migrate old preferences.json to new schema"""
    
    if not os.path.exists(config_path):
        print(f"❌ No preferences file found at {config_path}")
        return False
        
    # Backup existing file
    backup_path = f"{config_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(config_path, backup_path)
    print(f"✅ Backed up existing preferences to {backup_path}")
    
    # Load existing preferences
    with open(config_path, 'r') as f:
        old_prefs = json.load(f)
    
    # Check if already migrated
    if old_prefs.get('version') == '2.0':
        print("✅ Preferences already migrated to version 2.0")
        return True
        
    print("🔄 Migrating preferences to new schema...")
    
    # Create new structure
    new_prefs = {
        "version": "2.0",
        "partner_preferences": {
            "physical": {
                "reference_images": [],  # Will be populated by user
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
                "shared_interests": old_prefs.get('interests', {}).get('preferred', []),
                "importance_weight": 0.1,
                "dealbreaker_interests": old_prefs.get('interests', {}).get('dealbreakers', [])
            }
        },
        "matching_criteria": {
            "minimum_score": old_prefs.get('swipe_threshold', 0.6),
            "super_like_score": old_prefs.get('super_like_threshold', 0.85),
            "diversity_factor": 0.2,
            "recency_weight": 0.1
        },
        # Preserve existing structure for backward compatibility
        "age_range": old_prefs.get('age_range', {"min": 25, "max": 35}),
        "bio_keywords": old_prefs.get('bio_keywords', {
            "positive": [],
            "negative": [],
            "required": []
        }),
        "messaging": old_prefs.get('messaging', {}),
        "automation": old_prefs.get('automation', {
            "swipe_threshold": 0.6,
            "super_like_threshold": 0.85,
            "max_swipes_per_hour": 100,
            "min_delay_seconds": 2,
            "max_delay_seconds": 5,
            "auto_message": True,
            "auto_swipe": True,
            "hours_active": ["09:00", "23:00"]
        }),
        "date_preferences": old_prefs.get('date_preferences', {})
    }
    
    # Migrate bio keywords to personality traits if available
    if old_prefs.get('bio_keywords', {}).get('positive'):
        personality_traits = []
        positive_keywords = old_prefs['bio_keywords']['positive']
        
        # Map common bio keywords to personality traits
        trait_mapping = {
            'fitness': 'health-conscious',
            'gym': 'fitness-oriented', 
            'travel': 'adventurous',
            'adventure': 'adventurous',
            'professional': 'career-focused',
            'ambitious': 'ambitious',
            'entrepreneur': 'entrepreneurial',
            'creative': 'creative',
            'music': 'artistic',
            'art': 'artistic',
            'reading': 'intellectual',
            'foodie': 'food-loving',
            'coffee': 'social',
            'wine': 'sophisticated'
        }
        
        for keyword in positive_keywords:
            if keyword.lower() in trait_mapping:
                trait = trait_mapping[keyword.lower()]
                if trait not in personality_traits:
                    personality_traits.append(trait)
        
        new_prefs["partner_preferences"]["personality"]["traits"] = personality_traits
    
    # Save migrated preferences
    with open(config_path, 'w') as f:
        json.dump(new_prefs, f, indent=2)
    
    print("✅ Migration completed successfully!")
    
    # Show summary of changes
    print("\n📊 Migration Summary:")
    print(f"  • Version upgraded to: 2.0")
    print(f"  • Physical importance weight: {new_prefs['partner_preferences']['physical']['importance_weight']}")
    print(f"  • Personality importance weight: {new_prefs['partner_preferences']['personality']['importance_weight']}")
    print(f"  • Interest importance weight: {new_prefs['partner_preferences']['interests']['importance_weight']}")
    print(f"  • Migrated {len(new_prefs['partner_preferences']['interests']['shared_interests'])} interests")
    print(f"  • Migrated {len(new_prefs['partner_preferences']['personality']['traits'])} personality traits")
    print(f"  • Backup saved to: {backup_path}")
    
    print("\n💡 Next Steps:")
    print("  1. Run: python preference_cli.py setup")
    print("  2. Add reference images of your ideal partner")
    print("  3. Fine-tune personality and interest preferences")
    
    return True


def main():
    """Main migration entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate preferences to new schema')
    parser.add_argument('--config', default='config/preferences.json',
                       help='Path to preferences file')
    
    args = parser.parse_args()
    
    try:
        success = migrate_preferences(args.config)
        if success:
            print("\n🎉 Migration completed successfully!")
        else:
            print("\n❌ Migration failed.")
    except Exception as e:
        print(f"\n❌ Migration error: {e}")


if __name__ == "__main__":
    main()