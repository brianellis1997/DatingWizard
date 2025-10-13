"""
Add image_embedding column to classification_results table

This migration adds support for storing CLIP image embeddings (512-dimensional vectors)
as binary blobs in the database for faster training.

Usage:
    python backend/migrations/add_embeddings_column.py
"""

import sqlite3
import sys
import os

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

def run_migration():
    db_path = "data/dating_wizard.db"

    print(f"🔄 Running migration: Add image_embedding column")
    print(f"📍 Database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(classification_results)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'image_embedding' in columns:
            print("✅ Column 'image_embedding' already exists. Skipping migration.")
            return

        # Add image_embedding column
        print("➕ Adding 'image_embedding' column...")
        cursor.execute("""
            ALTER TABLE classification_results
            ADD COLUMN image_embedding BLOB
        """)

        # Add text_embedding column (for bio embeddings in future)
        print("➕ Adding 'text_embedding' column...")
        cursor.execute("""
            ALTER TABLE classification_results
            ADD COLUMN text_embedding BLOB
        """)

        # Add embedding_model_version to track which model created embeddings
        print("➕ Adding 'embedding_model_version' column...")
        cursor.execute("""
            ALTER TABLE classification_results
            ADD COLUMN embedding_model_version VARCHAR
        """)

        conn.commit()

        print("✅ Migration completed successfully!")
        print(f"📊 Added 3 new columns:")
        print(f"   - image_embedding (BLOB): CLIP image embeddings (512-dim)")
        print(f"   - text_embedding (BLOB): CLIP text embeddings (512-dim)")
        print(f"   - embedding_model_version (VARCHAR): Model used for embeddings")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
