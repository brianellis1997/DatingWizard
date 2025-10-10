#!/usr/bin/env python3
"""
Classifier Evaluation Script - Measure accuracy and performance
"""

import sys
import os
import json
import argparse
from pathlib import Path
from typing import List, Dict, Tuple
import time

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.analyzers.dating_classifier import DatingClassifier
from loguru import logger


class EvaluationDataset:
    """Manages labeled test dataset"""

    def __init__(self, dataset_path: str):
        self.dataset_path = Path(dataset_path)
        self.samples = []
        self._load_dataset()

    def _load_dataset(self):
        """Load dataset from directory structure or JSON file"""
        # Check if JSON manifest exists
        manifest_path = self.dataset_path / "dataset.json"

        if manifest_path.exists():
            with open(manifest_path, 'r') as f:
                data = json.load(f)
                self.samples = data.get('samples', [])
        else:
            # Load from directory structure: matches/ and non_matches/
            matches_dir = self.dataset_path / "matches"
            non_matches_dir = self.dataset_path / "non_matches"

            if matches_dir.exists():
                for img_path in matches_dir.glob("*.{jpg,jpeg,png}"):
                    self.samples.append({
                        'path': str(img_path),
                        'label': True,
                        'name': img_path.stem
                    })

            if non_matches_dir.exists():
                for img_path in non_matches_dir.glob("*.{jpg,jpeg,png}"):
                    self.samples.append({
                        'path': str(img_path),
                        'label': False,
                        'name': img_path.stem
                    })

        logger.info(f"Loaded {len(self.samples)} samples from dataset")

    def get_samples(self) -> List[Dict]:
        """Get all samples"""
        return self.samples


class ClassifierEvaluator:
    """Evaluates classifier performance"""

    def __init__(self, classifier: DatingClassifier):
        self.classifier = classifier

    def evaluate(self, dataset: EvaluationDataset) -> Dict:
        """
        Evaluate classifier on test dataset

        Returns evaluation metrics including accuracy, precision, recall, F1
        """
        samples = dataset.get_samples()

        if not samples:
            raise ValueError("No samples in dataset")

        print(f"\n{'='*60}")
        print(f"🧪 EVALUATING CLASSIFIER")
        print(f"{'='*60}")
        print(f"Test samples: {len(samples)}")

        # Initialize metrics
        true_positives = 0
        true_negatives = 0
        false_positives = 0
        false_negatives = 0

        all_predictions = []
        all_labels = []
        all_confidences = []

        processing_times = []

        # Evaluate each sample
        for i, sample in enumerate(samples, 1):
            print(f"\rProcessing {i}/{len(samples)}...", end='', flush=True)

            try:
                start_time = time.time()
                result = self.classifier.classify_screenshot(sample['path'])
                processing_time = time.time() - start_time

                processing_times.append(processing_time)

                predicted = result.is_match
                actual = sample['label']

                all_predictions.append(predicted)
                all_labels.append(actual)
                all_confidences.append(result.confidence_score)

                # Update confusion matrix
                if predicted and actual:
                    true_positives += 1
                elif not predicted and not actual:
                    true_negatives += 1
                elif predicted and not actual:
                    false_positives += 1
                elif not predicted and actual:
                    false_negatives += 1

            except Exception as e:
                logger.error(f"Error processing {sample['path']}: {e}")

        print()  # New line after progress

        # Calculate metrics
        total = len(samples)
        accuracy = (true_positives + true_negatives) / total if total > 0 else 0

        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0

        metrics = {
            'total_samples': total,
            'true_positives': true_positives,
            'true_negatives': true_negatives,
            'false_positives': false_positives,
            'false_negatives': false_negatives,
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1_score,
            'avg_processing_time': avg_processing_time,
            'avg_confidence': sum(all_confidences) / len(all_confidences) if all_confidences else 0
        }

        return metrics

    def print_metrics(self, metrics: Dict):
        """Print evaluation metrics in a nice format"""
        print(f"\n{'='*60}")
        print(f"📊 EVALUATION RESULTS")
        print(f"{'='*60}")

        print(f"\nConfusion Matrix:")
        print(f"                 Predicted")
        print(f"                 Match  | No Match")
        print(f"         Match   {metrics['true_positives']:5d}  | {metrics['false_negatives']:5d}")
        print(f"  Actual        --------|----------")
        print(f"      No Match  {metrics['false_positives']:5d}  | {metrics['true_negatives']:5d}")

        print(f"\nPerformance Metrics:")
        print(f"  • Accuracy:  {metrics['accuracy']:.1%}")
        print(f"  • Precision: {metrics['precision']:.1%}")
        print(f"  • Recall:    {metrics['recall']:.1%}")
        print(f"  • F1 Score:  {metrics['f1_score']:.1%}")

        print(f"\nAdditional Stats:")
        print(f"  • Avg Confidence:     {metrics['avg_confidence']:.1%}")
        print(f"  • Avg Processing Time: {metrics['avg_processing_time']:.3f}s")
        print(f"  • Total Samples:      {metrics['total_samples']}")

        print(f"{'='*60}\n")

        # Interpretation
        print("💡 Interpretation:")
        if metrics['accuracy'] >= 0.80:
            print("  ✅ Excellent accuracy! Classifier is performing very well.")
        elif metrics['accuracy'] >= 0.70:
            print("  ✅ Good accuracy. Classifier is reliable for most cases.")
        elif metrics['accuracy'] >= 0.60:
            print("  ⚠️  Moderate accuracy. Consider adding more training data.")
        else:
            print("  ❌ Low accuracy. Needs more training data or weight adjustment.")

        if metrics['precision'] < 0.70:
            print("  ⚠️  Low precision - many false positives (incorrectly classifying as matches)")

        if metrics['recall'] < 0.70:
            print("  ⚠️  Low recall - missing many actual matches (false negatives)")

    def analyze_errors(self, dataset: EvaluationDataset) -> List[Dict]:
        """Analyze misclassified samples"""
        samples = dataset.get_samples()
        errors = []

        for sample in samples:
            try:
                result = self.classifier.classify_screenshot(sample['path'])
                predicted = result.is_match
                actual = sample['label']

                if predicted != actual:
                    errors.append({
                        'path': sample['path'],
                        'name': sample.get('name', Path(sample['path']).stem),
                        'predicted': predicted,
                        'actual': actual,
                        'confidence': result.confidence_score,
                        'scores': result.component_scores
                    })

            except Exception as e:
                logger.error(f"Error analyzing {sample['path']}: {e}")

        return errors

    def print_error_analysis(self, errors: List[Dict]):
        """Print detailed error analysis"""
        if not errors:
            print("\n✅ No misclassifications!")
            return

        print(f"\n{'='*60}")
        print(f"❌ ERROR ANALYSIS ({len(errors)} misclassifications)")
        print(f"{'='*60}")

        # Separate into false positives and false negatives
        false_positives = [e for e in errors if e['predicted'] and not e['actual']]
        false_negatives = [e for e in errors if not e['predicted'] and e['actual']]

        if false_positives:
            print(f"\n🔴 False Positives ({len(false_positives)}) - Incorrectly classified as matches:")
            for i, error in enumerate(false_positives[:5], 1):
                print(f"  {i}. {error['name']}")
                print(f"     Confidence: {error['confidence']:.1%}")
                print(f"     Scores - Physical: {error['scores']['physical']:.1%}, "
                      f"Personality: {error['scores']['personality']:.1%}, "
                      f"Interests: {error['scores']['interests']:.1%}")

        if false_negatives:
            print(f"\n🔵 False Negatives ({len(false_negatives)}) - Missed actual matches:")
            for i, error in enumerate(false_negatives[:5], 1):
                print(f"  {i}. {error['name']}")
                print(f"     Confidence: {error['confidence']:.1%}")
                print(f"     Scores - Physical: {error['scores']['physical']:.1%}, "
                      f"Personality: {error['scores']['personality']:.1%}, "
                      f"Interests: {error['scores']['interests']:.1%}")

        print(f"{'='*60}\n")


def create_sample_dataset():
    """Create a sample dataset structure for testing"""
    dataset_dir = Path("data/test_profiles")
    dataset_dir.mkdir(parents=True, exist_ok=True)

    (dataset_dir / "matches").mkdir(exist_ok=True)
    (dataset_dir / "non_matches").mkdir(exist_ok=True)

    readme = dataset_dir / "README.txt"
    readme.write_text("""
Test Dataset Structure
======================

Place labeled screenshots in these directories:

matches/        - Screenshots of profiles you would match with
non_matches/    - Screenshots of profiles you would not match with

The evaluation script will automatically load these images and test the classifier.

Alternatively, create a dataset.json file with this structure:
{
  "samples": [
    {"path": "path/to/screenshot.jpg", "label": true, "name": "Profile 1"},
    {"path": "path/to/screenshot2.jpg", "label": false, "name": "Profile 2"}
  ]
}
""")

    print(f"✅ Created sample dataset structure at {dataset_dir}")
    print(f"📝 See {readme} for instructions")


def main():
    parser = argparse.ArgumentParser(description='Evaluate Dating Classifier')
    parser.add_argument('--dataset', default='data/test_profiles',
                       help='Path to test dataset directory')
    parser.add_argument('--config', default='config/preferences.json',
                       help='Path to preferences config')
    parser.add_argument('--create-dataset', action='store_true',
                       help='Create sample dataset structure')
    parser.add_argument('--export', help='Export metrics to JSON file')
    parser.add_argument('--error-analysis', action='store_true',
                       help='Perform detailed error analysis')

    args = parser.parse_args()

    if args.create_dataset:
        create_sample_dataset()
        return 0

    # Initialize classifier
    print("🚀 Initializing classifier...")
    try:
        classifier = DatingClassifier(args.config)
    except Exception as e:
        print(f"❌ Failed to initialize classifier: {e}")
        return 1

    # Load dataset
    try:
        dataset = EvaluationDataset(args.dataset)
    except Exception as e:
        print(f"❌ Failed to load dataset: {e}")
        print(f"\n💡 Tip: Run with --create-dataset to create dataset structure")
        return 1

    if not dataset.get_samples():
        print(f"❌ No samples found in dataset at {args.dataset}")
        print(f"💡 Tip: Run with --create-dataset to create dataset structure")
        return 1

    # Evaluate
    evaluator = ClassifierEvaluator(classifier)
    metrics = evaluator.evaluate(dataset)
    evaluator.print_metrics(metrics)

    # Error analysis
    if args.error_analysis:
        errors = evaluator.analyze_errors(dataset)
        evaluator.print_error_analysis(errors)

    # Export results
    if args.export:
        os.makedirs(os.path.dirname(args.export), exist_ok=True)
        with open(args.export, 'w') as f:
            json.dump(metrics, f, indent=2)
        print(f"✅ Metrics exported to {args.export}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
