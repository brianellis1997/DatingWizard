#!/usr/bin/env python3
"""
Instagram Classifier Pipeline - End-to-end Instagram profile discovery and classification
"""

import sys
import os
import argparse
from pathlib import Path
import json
from datetime import datetime
from typing import List, Dict
import time

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.analyzers.dating_classifier import DatingClassifier
from src.scrapers.instagram_scraper import InstagramScraper
from src.scrapers import SourceType
from loguru import logger


class InstagramClassifierPipeline:
    """Pipeline for finding and classifying Instagram profiles"""

    def __init__(self, preferences_path: str = "config/preferences.json"):
        logger.info("Initializing Instagram Classifier Pipeline...")

        self.classifier = DatingClassifier(preferences_path)
        self.scraper = InstagramScraper(use_selenium=True, headless=False)

        # Output directories
        self.screenshots_dir = Path("data/instagram_screenshots")
        self.results_dir = Path("data/instagram_results")
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def search_and_classify(self, query: str, limit: int = 20,
                          min_match_score: float = 0.6) -> List[Dict]:
        """
        Search Instagram and classify profiles

        Args:
            query: Search query (hashtag, location, or username)
            limit: Maximum profiles to analyze
            min_match_score: Minimum score to consider as match

        Returns:
            List of matched profiles with classification results
        """
        print(f"\n{'='*60}")
        print(f"🔍 Instagram Profile Search & Classification")
        print(f"{'='*60}")
        print(f"Query: {query}")
        print(f"Limit: {limit} profiles")
        print(f"Min Match Score: {min_match_score:.1%}")
        print(f"{'='*60}\n")

        # Search Instagram
        print("📱 Searching Instagram...")
        search_result = self.scraper.search_profiles(query, limit=limit)

        if not search_result.profiles:
            print("❌ No profiles found")
            return []

        print(f"✅ Found {len(search_result.profiles)} profiles")
        print(f"⏱️  Search took {search_result.execution_time:.1f}s\n")

        # Classify each profile
        matches = []
        session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for i, profile in enumerate(search_result.profiles, 1):
            print(f"\n[{i}/{len(search_result.profiles)}] Analyzing: {profile.name or profile.source_id}")
            print("-" * 40)

            try:
                # Take screenshot or use profile image
                screenshot_path = self._get_profile_screenshot(profile, session_timestamp, i)

                if not screenshot_path or not os.path.exists(screenshot_path):
                    print("  ⚠️  Could not get screenshot, skipping...")
                    continue

                # Classify
                result = self.classifier.classify_screenshot(screenshot_path)

                # Display result
                if result.is_match:
                    print(f"  ✅ MATCH ({result.confidence_score:.1%})")
                else:
                    print(f"  ❌ No match ({result.confidence_score:.1%})")

                print(f"  Physical: {result.component_scores['physical']:.1%} | "
                      f"Personality: {result.component_scores['personality']:.1%} | "
                      f"Interests: {result.component_scores['interests']:.1%}")

                if result.reasons:
                    print(f"  💡 {result.reasons[0]}")

                # Save if match
                if result.is_match and result.confidence_score >= min_match_score:
                    match_data = {
                        'profile': {
                            'username': profile.source_id,
                            'name': profile.name,
                            'bio': profile.bio,
                            'url': profile.url,
                            'followers': profile.followers,
                            'image_urls': profile.profile_images
                        },
                        'classification': result.to_dict(),
                        'screenshot_path': screenshot_path,
                        'timestamp': datetime.now().isoformat()
                    }
                    matches.append(match_data)

                # Rate limiting
                time.sleep(2)

            except Exception as e:
                logger.error(f"Error processing profile {profile.source_id}: {e}")
                print(f"  ❌ Error: {e}")

        # Save results
        if matches:
            results_file = self.results_dir / f"matches_{session_timestamp}.json"
            with open(results_file, 'w') as f:
                json.dump(matches, f, indent=2)

            print(f"\n✅ Saved {len(matches)} matches to {results_file}")

        return matches

    def _get_profile_screenshot(self, profile, session_id: str, index: int) -> str:
        """
        Get screenshot for profile
        For now, creates a composite from profile data
        In production, would use Selenium to capture actual profile page
        """
        try:
            # Create screenshot filename
            safe_username = "".join(c for c in profile.source_id if c.isalnum() or c in "._-")
            screenshot_path = self.screenshots_dir / f"{session_id}_{index:03d}_{safe_username}.png"

            # If profile has images, download and create composite
            if profile.profile_images:
                # Simple approach: use first profile image as screenshot
                # In production, would create actual screenshot of full profile
                import requests
                from PIL import Image, ImageDraw, ImageFont
                import io

                # Download first image
                img_url = profile.profile_images[0]
                response = requests.get(img_url, timeout=10)

                if response.status_code == 200:
                    img = Image.open(io.BytesIO(response.content))

                    # Resize to standard size
                    img = img.resize((800, 1000), Image.Resampling.LANCZOS)

                    # Add bio text as overlay (simple mockup)
                    draw = ImageDraw.Draw(img)
                    if profile.bio:
                        # Simple text overlay at bottom
                        try:
                            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
                        except:
                            font = ImageFont.load_default()

                        bio_text = profile.bio[:150] if profile.bio else ""
                        # Draw semi-transparent background for text
                        draw.rectangle([0, 850, 800, 1000], fill=(0, 0, 0, 180))
                        draw.text((20, 870), bio_text, fill='white', font=font)

                    # Save
                    img.save(screenshot_path)
                    return str(screenshot_path)

            return None

        except Exception as e:
            logger.error(f"Error creating screenshot: {e}")
            return None

    def analyze_saved_results(self, results_file: str):
        """Analyze previously saved results"""
        with open(results_file, 'r') as f:
            matches = json.load(f)

        print(f"\n{'='*60}")
        print(f"📊 ANALYSIS OF SAVED RESULTS")
        print(f"{'='*60}")
        print(f"Total matches: {len(matches)}")

        if not matches:
            print("No matches to analyze")
            return

        # Sort by confidence
        sorted_matches = sorted(matches, key=lambda m: m['classification']['confidence_score'], reverse=True)

        # Top matches
        print(f"\n🌟 TOP 5 MATCHES:\n")
        for i, match in enumerate(sorted_matches[:5], 1):
            profile = match['profile']
            classification = match['classification']

            print(f"{i}. @{profile['username']}")
            if profile['name']:
                print(f"   Name: {profile['name']}")
            print(f"   Score: {classification['confidence_score']:.1%}")
            print(f"   Physical: {classification['component_scores']['physical']:.1%} | "
                  f"Personality: {classification['component_scores']['personality']:.1%} | "
                  f"Interests: {classification['component_scores']['interests']:.1%}")

            if classification['reasons']:
                print(f"   💡 {classification['reasons'][0]}")

            if profile.get('bio'):
                bio = profile['bio'][:80] + "..." if len(profile['bio']) > 80 else profile['bio']
                print(f"   Bio: {bio}")

            print(f"   URL: {profile['url']}")
            print()

        # Statistics
        avg_score = sum(m['classification']['confidence_score'] for m in matches) / len(matches)
        avg_physical = sum(m['classification']['component_scores']['physical'] for m in matches) / len(matches)
        avg_personality = sum(m['classification']['component_scores']['personality'] for m in matches) / len(matches)
        avg_interests = sum(m['classification']['component_scores']['interests'] for m in matches) / len(matches)

        print(f"📊 STATISTICS:")
        print(f"  Average match score: {avg_score:.1%}")
        print(f"  Average physical score: {avg_physical:.1%}")
        print(f"  Average personality score: {avg_personality:.1%}")
        print(f"  Average interest score: {avg_interests:.1%}")

        # Distribution
        high_matches = [m for m in matches if m['classification']['confidence_score'] >= 0.8]
        medium_matches = [m for m in matches if 0.6 <= m['classification']['confidence_score'] < 0.8]
        low_matches = [m for m in matches if m['classification']['confidence_score'] < 0.6]

        print(f"\n📈 DISTRIBUTION:")
        print(f"  High confidence (≥80%): {len(high_matches)}")
        print(f"  Medium confidence (60-80%): {len(medium_matches)}")
        print(f"  Low confidence (<60%): {len(low_matches)}")

    def list_saved_results(self):
        """List all saved result files"""
        result_files = sorted(self.results_dir.glob("matches_*.json"), reverse=True)

        if not result_files:
            print("No saved results found")
            return

        print(f"\n📂 SAVED RESULTS ({len(result_files)} files):\n")
        for i, file in enumerate(result_files[:10], 1):
            with open(file, 'r') as f:
                matches = json.load(f)

            timestamp = file.stem.replace('matches_', '')
            print(f"{i}. {file.name}")
            print(f"   Matches: {len(matches)}")
            print(f"   Timestamp: {timestamp}")
            print()

    def cleanup(self):
        """Clean up resources"""
        if self.scraper:
            self.scraper.close()


def main():
    parser = argparse.ArgumentParser(description='Instagram Classifier Pipeline')
    parser.add_argument('--query', help='Instagram search query')
    parser.add_argument('--limit', type=int, default=20,
                       help='Maximum profiles to analyze (default: 20)')
    parser.add_argument('--min-score', type=float, default=0.6,
                       help='Minimum match score (default: 0.6)')
    parser.add_argument('--config', default='config/preferences.json',
                       help='Preferences config path')
    parser.add_argument('--analyze', help='Analyze saved results file')
    parser.add_argument('--list-results', action='store_true',
                       help='List saved result files')

    args = parser.parse_args()

    try:
        pipeline = InstagramClassifierPipeline(args.config)

        if args.list_results:
            pipeline.list_saved_results()
            return 0

        if args.analyze:
            pipeline.analyze_saved_results(args.analyze)
            return 0

        if not args.query:
            print("❌ --query required (or use --list-results or --analyze)")
            return 1

        # Run pipeline
        matches = pipeline.search_and_classify(
            query=args.query,
            limit=args.limit,
            min_match_score=args.min_score
        )

        # Summary
        print(f"\n{'='*60}")
        print(f"🎉 PIPELINE COMPLETE")
        print(f"{'='*60}")
        print(f"Analyzed: {args.limit} profiles")
        print(f"Matches found: {len(matches)}")

        if matches:
            print(f"\n💫 Recommended next steps:")
            print(f"  1. Review matches in data/instagram_results/")
            print(f"  2. Visit profiles on Instagram")
            print(f"  3. Update preferences based on results")

        return 0

    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        print(f"❌ Error: {e}")
        return 1
    finally:
        if 'pipeline' in locals():
            pipeline.cleanup()


if __name__ == "__main__":
    sys.exit(main())
