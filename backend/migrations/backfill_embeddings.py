"""
Backfill embeddings for existing classification results

This script extracts CLIP embeddings for all existing classification results
that have user feedback but no embeddings yet.

Usage:
    python backend/migrations/backfill_embeddings.py
"""

import sys
import os
import pickle
from pathlib import Path

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.database.db import SessionLocal
from backend.database.models import ClassificationResult
from backend.services.classifier_service import get_classifier_service
from loguru import logger

def backfill_embeddings():
    """Extract and save embeddings for existing results"""

    db = SessionLocal()
    classifier_service = get_classifier_service()

    try:
        # Get all results with feedback but no embedding
        results = db.query(ClassificationResult).filter(
            ClassificationResult.user_feedback.isnot(None),
            ClassificationResult.image_embedding.is_(None)
        ).all()

        if not results:
            print("✅ No results need backfilling. All feedback examples already have embeddings!")
            return

        print(f"🔄 Found {len(results)} results that need embeddings")
        print(f"📊 Feedback breakdown:")

        feedback_counts = {}
        for r in results:
            feedback_counts[r.user_feedback] = feedback_counts.get(r.user_feedback, 0) + 1

        for feedback, count in feedback_counts.items():
            print(f"   - {feedback}: {count}")

        print(f"\n⏳ Extracting embeddings (this may take a minute)...\n")

        success_count = 0
        fail_count = 0

        for i, result in enumerate(results, 1):
            print(f"[{i}/{len(results)}] Processing {Path(result.screenshot_path).name}...", end=" ")

            # Check if image file exists
            if not os.path.exists(result.screenshot_path):
                print(f"❌ Image not found")
                fail_count += 1
                continue

            # Extract embedding
            if hasattr(classifier_service.classifier, 'extract_embedding'):
                embedding = classifier_service.classifier.extract_embedding(result.screenshot_path)

                if embedding is not None:
                    # Serialize and save
                    result.image_embedding = pickle.dumps(embedding)
                    result.embedding_model_version = "openai/clip-vit-base-patch32"

                    print(f"✅ Saved ({embedding.shape})")
                    success_count += 1
                else:
                    print(f"❌ Failed to extract")
                    fail_count += 1
            else:
                print(f"❌ Classifier doesn't support embeddings")
                fail_count += 1

        # Commit all changes
        db.commit()

        print(f"\n" + "="*60)
        print(f"✅ Backfill complete!")
        print(f"   - Success: {success_count}/{len(results)}")
        print(f"   - Failed: {fail_count}/{len(results)}")
        print(f"="*60)

        # Verify
        remaining = db.query(ClassificationResult).filter(
            ClassificationResult.user_feedback.isnot(None),
            ClassificationResult.image_embedding.is_(None)
        ).count()

        if remaining == 0:
            print(f"\n🎉 All feedback examples now have embeddings!")
            print(f"📈 Ready for model training with {success_count} examples")
        else:
            print(f"\n⚠️  {remaining} results still missing embeddings")

    except Exception as e:
        logger.error(f"Backfill failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("="*60)
    print("  CLIP Embedding Backfill Script")
    print("="*60)
    backfill_embeddings()
