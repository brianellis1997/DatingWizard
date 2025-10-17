#!/usr/bin/env python3
"""Monitor Instagram scraping progress"""

import sys
import os
sys.path.insert(0, '/app')

from backend.database.connection import SessionLocal
from backend.database.models import InstagramResult
from sqlalchemy import func
from datetime import datetime, timedelta
import time

def monitor_progress():
    db = SessionLocal()

    try:
        # Get total count
        total = db.query(InstagramResult).count()

        # Get count from last hour
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent = db.query(InstagramResult).filter(InstagramResult.created_at >= one_hour_ago).count()

        # Get count with embeddings
        with_embeddings = db.query(InstagramResult).filter(InstagramResult.embedding.isnot(None)).count()

        # Get count with feedback
        with_feedback = db.query(InstagramResult).filter(InstagramResult.user_feedback.isnot(None)).count()

        # Get latest 10 profiles
        latest = db.query(
            InstagramResult.username,
            InstagramResult.created_at,
            InstagramResult.clip_score,
            InstagramResult.user_feedback,
            InstagramResult.profile_image_url
        ).order_by(InstagramResult.created_at.desc()).limit(10).all()

        print('=' * 80)
        print(f'INSTAGRAM SCRAPING PROGRESS - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        print('=' * 80)
        print(f'Total profiles scraped: {total}')
        print(f'Scraped in last hour: {recent}')
        print(f'With embeddings: {with_embeddings}/{total} ({100*with_embeddings//total if total > 0 else 0}%)')
        print(f'With feedback: {with_feedback}/{total} ({100*with_feedback//total if total > 0 else 0}%)')
        print()
        print('Latest 10 profiles:')
        print('-' * 80)
        print(f"{'Username':<20} {'Score':<8} {'Feedback':<12} {'Image':<8} {'Time':<20}")
        print('-' * 80)

        for username, created_at, score, feedback, img_url in latest:
            score_str = f"{score:.3f}" if score else "N/A"
            feedback_str = feedback or "pending"
            img_status = "✓" if img_url else "✗"
            time_str = created_at.strftime("%H:%M:%S") if created_at else "N/A"
            print(f"{username:<20} {score_str:<8} {feedback_str:<12} {img_status:<8} {time_str:<20}")

        print('=' * 80)
        print()

    finally:
        db.close()

if __name__ == "__main__":
    monitor_progress()
