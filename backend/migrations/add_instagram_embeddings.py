"""
Add embedding and CLIP classification columns to instagram_results table

This migration adds:
- screenshot_path: Path to profile screenshot
- image_embedding: CLIP image embedding (512-dim vector)
- embedding_model_version: Which CLIP model created the embedding
- confidence_score, physical_score, personality_score, interest_score: CLIP scores
- is_match: Whether profile passes threshold
- user_feedback: User rating (like/dislike/super_like)
- feedback_at: Timestamp of feedback

Usage:
    python backend/migrations/add_instagram_embeddings.py
"""

import sqlite3
import sys
import os

def run_migration():
    db_path = "data/dating_wizard.db"

    print(f"🔄 Running migration: Add Instagram embeddings and CLIP scores")
    print(f"📍 Database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check existing columns
        cursor.execute("PRAGMA table_info(instagram_results)")
        existing_columns = {col[1] for col in cursor.fetchall()}

        columns_to_add = [
            ("screenshot_path", "TEXT"),
            ("image_embedding", "BLOB"),
            ("embedding_model_version", "VARCHAR"),
            ("confidence_score", "FLOAT"),
            ("physical_score", "FLOAT"),
            ("personality_score", "FLOAT"),
            ("interest_score", "FLOAT"),
            ("is_match", "BOOLEAN"),
            ("user_feedback", "VARCHAR"),
            ("feedback_at", "TIMESTAMP")
        ]

        added_count = 0
        for col_name, col_type in columns_to_add:
            if col_name not in existing_columns:
                print(f"➕ Adding '{col_name}' column ({col_type})...")
                cursor.execute(f"""
                    ALTER TABLE instagram_results
                    ADD COLUMN {col_name} {col_type}
                """)
                added_count += 1
            else:
                print(f"✓ Column '{col_name}' already exists")

        conn.commit()

        if added_count > 0:
            print(f"✅ Migration completed! Added {added_count} columns")
        else:
            print(f"✅ All columns already exist. No changes needed.")

        print(f"\n📊 instagram_results now supports:")
        print(f"   - Profile screenshots")
        print(f"   - CLIP embeddings (512-dim vectors)")
        print(f"   - Classification scores (physical/personality/interest)")
        print(f"   - User feedback for active learning")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
