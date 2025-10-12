"""
Migration script to add active learning tables and columns
Run this to upgrade the database schema
"""

import sys
import os
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text
from backend.database.db import engine
from loguru import logger


def run_migration():
    """Add active learning schema changes"""

    with engine.connect() as conn:
        try:
            # Create ModelVersion table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS model_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version_number INTEGER NOT NULL UNIQUE,
                    model_type VARCHAR NOT NULL,
                    model_path VARCHAR,
                    is_active BOOLEAN DEFAULT 0,
                    training_samples INTEGER DEFAULT 0,
                    training_accuracy FLOAT,
                    validation_accuracy FLOAT,
                    total_predictions INTEGER DEFAULT 0,
                    likes INTEGER DEFAULT 0,
                    dislikes INTEGER DEFAULT 0,
                    super_likes INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    trained_at TIMESTAMP
                )
            """))
            logger.info("✅ Created model_versions table")

            # Create TrainingJob table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS training_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_version_id INTEGER,
                    status VARCHAR DEFAULT 'pending',
                    epochs INTEGER DEFAULT 10,
                    batch_size INTEGER DEFAULT 32,
                    learning_rate FLOAT DEFAULT 0.001,
                    current_epoch INTEGER DEFAULT 0,
                    current_loss FLOAT,
                    current_accuracy FLOAT,
                    error_message TEXT,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (model_version_id) REFERENCES model_versions(id)
                )
            """))
            logger.info("✅ Created training_jobs table")

            # Check if columns already exist in classification_results
            result = conn.execute(text("PRAGMA table_info(classification_results)"))
            columns = {row[1] for row in result}

            if 'model_version_id' not in columns:
                # SQLite doesn't support ALTER TABLE ADD COLUMN with FOREIGN KEY
                # We need to create new table, copy data, drop old, rename new

                logger.info("Adding feedback columns to classification_results...")

                # Create new table with updated schema
                conn.execute(text("""
                    CREATE TABLE classification_results_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        screenshot_path VARCHAR NOT NULL,
                        is_match BOOLEAN NOT NULL,
                        confidence_score FLOAT NOT NULL,
                        physical_score FLOAT NOT NULL,
                        personality_score FLOAT NOT NULL,
                        interest_score FLOAT NOT NULL,
                        name VARCHAR,
                        age INTEGER,
                        bio TEXT,
                        model_version_id INTEGER,
                        user_feedback VARCHAR,
                        feedback_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (model_version_id) REFERENCES model_versions(id)
                    )
                """))

                # Copy existing data
                conn.execute(text("""
                    INSERT INTO classification_results_new
                        (id, screenshot_path, is_match, confidence_score, physical_score,
                         personality_score, interest_score, name, age, bio, created_at)
                    SELECT id, screenshot_path, is_match, confidence_score, physical_score,
                           personality_score, interest_score, name, age, bio, created_at
                    FROM classification_results
                """))

                # Drop old table
                conn.execute(text("DROP TABLE classification_results"))

                # Rename new table
                conn.execute(text("ALTER TABLE classification_results_new RENAME TO classification_results"))

                logger.info("✅ Added feedback columns to classification_results")
            else:
                logger.info("ℹ️  Feedback columns already exist in classification_results")

            # Create initial model version (ResNet50 baseline)
            result = conn.execute(text("SELECT COUNT(*) FROM model_versions"))
            count = result.scalar()

            if count == 0:
                conn.execute(text("""
                    INSERT INTO model_versions
                        (version_number, model_type, is_active, training_samples)
                    VALUES (1, 'resnet50', 1, 0)
                """))
                logger.info("✅ Created initial ResNet50 model version")

            conn.commit()
            logger.success("🎉 Migration completed successfully!")

        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Migration failed: {e}")
            raise


if __name__ == "__main__":
    logger.info("Starting active learning migration...")
    run_migration()
