#!/usr/bin/env python3
"""
Preference Management CLI - Interactive tool for setting up AI partner preferences
"""

import sys
import os
from pathlib import Path
import argparse
from typing import List

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from utils.preference_manager import PreferenceManager
from loguru import logger


class PreferenceCLI:
    """Command-line interface for preference management"""
    
    def __init__(self):
        self.pref_manager = PreferenceManager()
        
    def setup_initial_preferences(self):
        """Interactive setup for first-time users"""
        print("\n🎯 Welcome to AI Partner Preference Setup!")
        print("Let's configure your ideal partner preferences.\n")
        
        # Physical preferences
        print("📸 PHYSICAL PREFERENCES")
        print("You can upload reference images of people you find attractive.")
        
        while True:
            add_image = input("Add a reference image? (y/n): ").lower()
            if add_image != 'y':
                break
                
            image_path = input("Enter path to image file: ").strip()
            if not os.path.exists(image_path):
                print("❌ File not found. Please try again.")
                continue
                
            category = input("Category (face/body/style/general) [general]: ").strip() or "general"
            description = input("Description (optional): ").strip()
            
            try:
                image_id = self.pref_manager.add_reference_image(image_path, category, description)
                print(f"✅ Added reference image: {image_id}")
            except Exception as e:
                print(f"❌ Error adding image: {e}")
                
        # Physical feature preferences
        print("\n🎭 PHYSICAL FEATURES")
        face_type = input("Preferred face type (oval/round/square/heart) []: ").strip()
        body_type = input("Preferred body type (slim/athletic/curvy/average) []: ").strip()
        height_pref = input("Height preference (tall/average/short/no-preference) []: ").strip()
        style_pref = input("Style preference (casual/formal/edgy/bohemian) []: ").strip()
        
        physical_weight = self._get_float_input("Physical importance weight (0.0-1.0) [0.6]: ", 0.6)
        
        self.pref_manager.update_physical_preferences(
            face_type=face_type,
            body_type=body_type,
            height_preference=height_pref,
            style_preference=style_pref,
            importance_weight=physical_weight
        )
        
        # Personality preferences
        print("\n🧠 PERSONALITY PREFERENCES")
        traits = self._get_list_input("Desired personality traits (comma-separated): ")
        comm_style = input("Communication style preference (direct/gentle/humor/intellectual) []: ").strip()
        lifestyle = self._get_list_input("Lifestyle compatibility (active/homebody/social/adventurous): ")
        
        personality_weight = self._get_float_input("Personality importance weight (0.0-1.0) [0.3]: ", 0.3)
        
        self.pref_manager.update_personality_preferences(
            traits=traits,
            communication_style=comm_style,
            lifestyle_compatibility=lifestyle,
            importance_weight=personality_weight
        )
        
        # Interest preferences
        print("\n🎨 INTEREST PREFERENCES")
        interests = self._get_list_input("Shared interests you value: ")
        dealbreakers = self._get_list_input("Interest dealbreakers: ")
        
        interest_weight = self._get_float_input("Interest importance weight (0.0-1.0) [0.1]: ", 0.1)
        
        self.pref_manager.update_interest_preferences(
            shared_interests=interests,
            dealbreaker_interests=dealbreakers,
            importance_weight=interest_weight
        )
        
        # Matching criteria
        print("\n⚙️ MATCHING CRITERIA")
        min_score = self._get_float_input("Minimum match score (0.0-1.0) [0.6]: ", 0.6)
        super_score = self._get_float_input("Super like score (0.0-1.0) [0.85]: ", 0.85)
        
        self.pref_manager.update_matching_criteria(
            minimum_score=min_score,
            super_like_score=super_score
        )
        
        print("\n✅ Preference setup complete!")
        self.show_summary()
        
    def add_reference_images(self, image_paths: List[str]):
        """Add multiple reference images"""
        for path in image_paths:
            if not os.path.exists(path):
                print(f"❌ File not found: {path}")
                continue
                
            category = input(f"Category for {Path(path).name} (face/body/style/general) [general]: ").strip() or "general"
            description = input(f"Description for {Path(path).name} (optional): ").strip()
            
            try:
                image_id = self.pref_manager.add_reference_image(path, category, description)
                print(f"✅ Added: {Path(path).name} -> {image_id}")
            except Exception as e:
                print(f"❌ Error adding {path}: {e}")
                
    def list_reference_images(self):
        """List all reference images"""
        images = self.pref_manager.get_reference_images()
        
        if not images:
            print("No reference images found.")
            return
            
        print(f"\n📸 Reference Images ({len(images)} total):")
        for img in images:
            print(f"  • {img['id'][:8]}... | {img['category']} | {img['filename']}")
            if img['description']:
                print(f"    Description: {img['description']}")
                
    def remove_reference_image(self, image_id: str):
        """Remove a reference image"""
        if self.pref_manager.remove_reference_image(image_id):
            print(f"✅ Removed reference image: {image_id}")
        else:
            print(f"❌ Image not found: {image_id}")
            
    def update_weights(self, physical: float = None, personality: float = None, interests: float = None):
        """Update importance weights"""
        if physical is not None:
            self.pref_manager.update_physical_preferences(importance_weight=physical)
            print(f"✅ Physical weight updated to {physical}")
            
        if personality is not None:
            self.pref_manager.update_personality_preferences(importance_weight=personality)
            print(f"✅ Personality weight updated to {personality}")
            
        if interests is not None:
            self.pref_manager.update_interest_preferences(importance_weight=interests)
            print(f"✅ Interest weight updated to {interests}")
            
    def show_summary(self):
        """Show preference summary"""
        summary = self.pref_manager.get_preference_summary()
        
        print("\n📊 PREFERENCE SUMMARY")
        print("="*50)
        print(f"Reference Images: {summary['reference_images_count']}")
        print(f"Physical Weight: {summary['physical_weight']}")
        print(f"Personality Weight: {summary['personality_weight']}")
        print(f"Interest Weight: {summary['interest_weight']}")
        print(f"Minimum Score: {summary['minimum_score']}")
        print(f"Personality Traits: {', '.join(summary['personality_traits'])}")
        print(f"Shared Interests: {', '.join(summary['shared_interests'])}")
        print("="*50)
        
    def export_config(self, export_path: str):
        """Export preferences to file"""
        try:
            self.pref_manager.export_preferences(export_path)
            print(f"✅ Preferences exported to {export_path}")
        except Exception as e:
            print(f"❌ Export failed: {e}")
            
    def import_config(self, import_path: str, merge: bool = True):
        """Import preferences from file"""
        try:
            self.pref_manager.import_preferences(import_path, merge)
            action = "merged" if merge else "replaced"
            print(f"✅ Preferences {action} from {import_path}")
        except Exception as e:
            print(f"❌ Import failed: {e}")
            
    def _get_list_input(self, prompt: str) -> List[str]:
        """Get comma-separated list input"""
        response = input(prompt).strip()
        if not response:
            return []
        return [item.strip() for item in response.split(',') if item.strip()]
        
    def _get_float_input(self, prompt: str, default: float) -> float:
        """Get float input with default"""
        response = input(prompt).strip()
        if not response:
            return default
        try:
            return float(response)
        except ValueError:
            print(f"Invalid input, using default: {default}")
            return default


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description='AI Partner Preference Manager')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Setup command
    setup_parser = subparsers.add_parser('setup', help='Interactive preference setup')
    
    # Add images command
    add_parser = subparsers.add_parser('add-images', help='Add reference images')
    add_parser.add_argument('images', nargs='+', help='Image file paths')
    
    # List images command
    list_parser = subparsers.add_parser('list-images', help='List reference images')
    
    # Remove image command
    remove_parser = subparsers.add_parser('remove-image', help='Remove reference image')
    remove_parser.add_argument('image_id', help='Image ID to remove')
    
    # Update weights command
    weights_parser = subparsers.add_parser('update-weights', help='Update importance weights')
    weights_parser.add_argument('--physical', type=float, help='Physical weight (0.0-1.0)')
    weights_parser.add_argument('--personality', type=float, help='Personality weight (0.0-1.0)')
    weights_parser.add_argument('--interests', type=float, help='Interest weight (0.0-1.0)')
    
    # Summary command
    summary_parser = subparsers.add_parser('summary', help='Show preference summary')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export preferences')
    export_parser.add_argument('path', help='Export file path')
    
    # Import command
    import_parser = subparsers.add_parser('import', help='Import preferences')
    import_parser.add_argument('path', help='Import file path')
    import_parser.add_argument('--replace', action='store_true', help='Replace instead of merge')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
        
    cli = PreferenceCLI()
    
    try:
        if args.command == 'setup':
            cli.setup_initial_preferences()
        elif args.command == 'add-images':
            cli.add_reference_images(args.images)
        elif args.command == 'list-images':
            cli.list_reference_images()
        elif args.command == 'remove-image':
            cli.remove_reference_image(args.image_id)
        elif args.command == 'update-weights':
            cli.update_weights(args.physical, args.personality, args.interests)
        elif args.command == 'summary':
            cli.show_summary()
        elif args.command == 'export':
            cli.export_config(args.path)
        elif args.command == 'import':
            cli.import_config(args.path, not args.replace)
            
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        logger.error(f"Command failed: {e}")
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()