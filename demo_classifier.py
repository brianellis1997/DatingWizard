#!/usr/bin/env python3
"""
Dating Classifier Demo - Interactive demonstration of the classification system
"""

import sys
import os
import argparse
from pathlib import Path
import json

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.analyzers.dating_classifier import DatingClassifier, ClassificationResult
from loguru import logger


def demo_single_screenshot(classifier: DatingClassifier, screenshot_path: str):
    """Classify a single screenshot and display results"""
    print(f"\n{'='*60}")
    print(f"🔍 Analyzing: {Path(screenshot_path).name}")
    print(f"{'='*60}")

    result = classifier.classify_screenshot(screenshot_path)
    print(result)


def demo_batch_screenshots(classifier: DatingClassifier, screenshot_dir: str):
    """Classify all screenshots in a directory"""
    screenshot_paths = []

    for ext in ['*.jpg', '*.jpeg', '*.png']:
        screenshot_paths.extend(Path(screenshot_dir).glob(ext))

    if not screenshot_paths:
        print(f"❌ No screenshots found in {screenshot_dir}")
        return

    print(f"\n🎯 Found {len(screenshot_paths)} screenshots to analyze\n")

    results = classifier.batch_classify([str(p) for p in screenshot_paths])

    matches = [r for r in results if r.is_match]
    non_matches = [r for r in results if not r.is_match]

    print(f"\n{'='*60}")
    print(f"📊 BATCH RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"Total analyzed: {len(results)}")
    print(f"Matches: {len(matches)} ({len(matches)/len(results)*100:.1f}%)")
    print(f"Non-matches: {len(non_matches)} ({len(non_matches)/len(results)*100:.1f}%)")
    print(f"Average confidence: {sum(r.confidence_score for r in results)/len(results):.1%}")

    # Show top matches
    if matches:
        print(f"\n🌟 TOP MATCHES:")
        sorted_matches = sorted(matches, key=lambda r: r.confidence_score, reverse=True)
        for i, result in enumerate(sorted_matches[:5], 1):
            name = result.extracted_data.get('name') or 'Unknown'
            age = result.extracted_data.get('age') or '?'
            print(f"  {i}. {name}, {age} - Confidence: {result.confidence_score:.1%}")
            print(f"     Screenshot: {Path(result.metadata['screenshot_path']).name}")
            if result.reasons:
                print(f"     Top reason: {result.reasons[0]}")
            print()


def demo_interactive(classifier: DatingClassifier):
    """Interactive mode - classify screenshots one by one"""
    print("\n🎮 INTERACTIVE MODE")
    print("="*60)
    print("Enter screenshot path to classify (or 'quit' to exit)")
    print("="*60)

    while True:
        path = input("\n📸 Screenshot path: ").strip()

        if path.lower() in ['quit', 'q', 'exit']:
            print("👋 Goodbye!")
            break

        if not os.path.exists(path):
            print(f"❌ File not found: {path}")
            continue

        demo_single_screenshot(classifier, path)

        save = input("\n💾 Save this result to file? (y/n): ").lower()
        if save == 'y':
            result = classifier.classify_screenshot(path)
            output_path = f"data/classification_results/{Path(path).stem}_result.json"
            os.makedirs("data/classification_results", exist_ok=True)

            with open(output_path, 'w') as f:
                json.dump(result.to_dict(), f, indent=2)

            print(f"✅ Saved to {output_path}")


def show_classifier_info(classifier: DatingClassifier):
    """Display information about the classifier"""
    stats = classifier.get_classifier_stats()

    print("\n📊 CLASSIFIER INFORMATION")
    print("="*60)
    print(f"Training Data:")
    print(f"  • Reference images: {stats['reference_images']}")
    print(f"  • Positive examples: {stats['positive_examples']}")
    print(f"  • Negative examples: {stats['negative_examples']}")
    print(f"  • Total: {stats['total_training_data']}")

    print(f"\nWeights:")
    print(f"  • Physical: {stats['weights']['physical']:.1%}")
    print(f"  • Personality: {stats['weights']['personality']:.1%}")
    print(f"  • Interests: {stats['weights']['interests']:.1%}")

    print(f"\nThresholds:")
    print(f"  • Minimum match score: {stats['min_score_threshold']:.1%}")
    print(f"  • Super like score: {stats['super_like_threshold']:.1%}")
    print("="*60)


def export_results(results: list, output_path: str, format: str = 'json'):
    """Export results to file"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    if format == 'json':
        with open(output_path, 'w') as f:
            json.dump([r.to_dict() for r in results], f, indent=2)
    elif format == 'csv':
        import csv
        with open(output_path, 'w', newline='') as f:
            if results:
                fieldnames = ['screenshot', 'is_match', 'confidence', 'physical_score',
                            'personality_score', 'interest_score', 'name', 'age']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for r in results:
                    writer.writerow({
                        'screenshot': Path(r.metadata['screenshot_path']).name,
                        'is_match': r.is_match,
                        'confidence': f"{r.confidence_score:.2%}",
                        'physical_score': f"{r.component_scores['physical']:.2%}",
                        'personality_score': f"{r.component_scores['personality']:.2%}",
                        'interest_score': f"{r.component_scores['interests']:.2%}",
                        'name': r.extracted_data.get('name', ''),
                        'age': r.extracted_data.get('age', '')
                    })

    print(f"✅ Exported {len(results)} results to {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Dating Classifier Demo')
    parser.add_argument('--mode', choices=['single', 'batch', 'interactive', 'info'],
                       default='interactive',
                       help='Demo mode (default: interactive)')
    parser.add_argument('--screenshot', help='Path to screenshot for single mode')
    parser.add_argument('--directory', help='Directory of screenshots for batch mode')
    parser.add_argument('--config', default='config/preferences.json',
                       help='Path to preferences config')
    parser.add_argument('--export', help='Export results to file')
    parser.add_argument('--format', choices=['json', 'csv'], default='json',
                       help='Export format')

    args = parser.parse_args()

    # Initialize classifier
    print("🚀 Initializing Dating Classifier...")
    try:
        classifier = DatingClassifier(args.config)
    except Exception as e:
        print(f"❌ Failed to initialize classifier: {e}")
        return 1

    if args.mode == 'info':
        show_classifier_info(classifier)
        return 0

    elif args.mode == 'single':
        if not args.screenshot:
            print("❌ --screenshot required for single mode")
            return 1

        demo_single_screenshot(classifier, args.screenshot)

        if args.export:
            result = classifier.classify_screenshot(args.screenshot)
            export_results([result], args.export, args.format)

    elif args.mode == 'batch':
        if not args.directory:
            print("❌ --directory required for batch mode")
            return 1

        demo_batch_screenshots(classifier, args.directory)

        if args.export:
            screenshot_paths = []
            for ext in ['*.jpg', '*.jpeg', '*.png']:
                screenshot_paths.extend(Path(args.directory).glob(ext))

            if screenshot_paths:
                results = classifier.batch_classify([str(p) for p in screenshot_paths])
                export_results(results, args.export, args.format)

    elif args.mode == 'interactive':
        show_classifier_info(classifier)
        demo_interactive(classifier)

    return 0


if __name__ == "__main__":
    sys.exit(main())
