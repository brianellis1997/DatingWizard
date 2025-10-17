#!/bin/bash
# Monitor Instagram scraping progress in real-time

echo "Monitoring Instagram Scraping Progress..."
echo "Press Ctrl+C to stop"
echo ""

while true; do
    clear
    docker exec dating-wizard-backend python -c "
import sqlite3
from datetime import datetime

conn = sqlite3.connect('data/dating_wizard.db')
cursor = conn.cursor()

# Get total count
cursor.execute('SELECT COUNT(*) FROM instagram_results')
total = cursor.fetchone()[0]

# Get recent count (last hour)
cursor.execute(\"SELECT COUNT(*) FROM instagram_results WHERE created_at >= datetime('now', '-1 hour')\")
recent = cursor.fetchone()[0]

# Get last 10 minutes
cursor.execute(\"SELECT COUNT(*) FROM instagram_results WHERE created_at >= datetime('now', '-10 minutes')\")
last_10min = cursor.fetchone()[0]

# Get with image embeddings
cursor.execute('SELECT COUNT(*) FROM instagram_results WHERE image_embedding IS NOT NULL')
with_embeddings = cursor.fetchone()[0]

# Get with feedback
cursor.execute('SELECT COUNT(*) FROM instagram_results WHERE user_feedback IS NOT NULL')
with_feedback = cursor.fetchone()[0]

# Get with profile images
cursor.execute('SELECT COUNT(*) FROM instagram_results WHERE profile_image_url IS NOT NULL')
with_images = cursor.fetchone()[0]

# Get with screenshots
cursor.execute('SELECT COUNT(*) FROM instagram_results WHERE screenshot_path IS NOT NULL')
with_screenshots = cursor.fetchone()[0]

# Get searches
cursor.execute('SELECT COUNT(*) FROM instagram_searches')
search_count = cursor.fetchone()[0]

print('=' * 80)
print(f'INSTAGRAM SCRAPING PROGRESS - {datetime.now().strftime(\"%Y-%m-%d %H:%M:%S\")}')
print('=' * 80)
print(f'Total profiles scraped: {total}')
print(f'  ├─ Last hour: {recent} profiles')
print(f'  ├─ Last 10 min: {last_10min} profiles')
print(f'  ├─ With profile images: {with_images}/{total}')
print(f'  ├─ With screenshots: {with_screenshots}/{total}')
print(f'  ├─ With embeddings: {with_embeddings}/{total}')
print(f'  └─ With feedback: {with_feedback}/{total}')
print()
print(f'Active searches: {search_count}')
print()

# Get latest profiles
cursor.execute('''
    SELECT username,
           ROUND(physical_score, 3) as phys_score,
           user_feedback,
           CASE WHEN profile_image_url IS NOT NULL THEN '✓' ELSE '✗' END as img,
           CASE WHEN screenshot_path IS NOT NULL THEN '✓' ELSE '✗' END as scrn,
           strftime('%H:%M:%S', created_at, 'localtime') as time
    FROM instagram_results
    ORDER BY created_at DESC
    LIMIT 15
''')

profiles = cursor.fetchall()

print('Latest 15 profiles:')
print('-' * 80)
print(f\"{'Username':<25} {'Score':<8} {'Feedback':<12} {'Img':<5} {'Scrn':<6} {'Time':<10}\")
print('-' * 80)

for username, score, feedback, img, scrn, time in profiles:
    score_str = f'{score:.3f}' if score else 'N/A'
    feedback_str = feedback or 'pending'
    print(f'{username:<25} {score_str:<8} {feedback_str:<12} {img:<5} {scrn:<6} {time:<10}')

print('=' * 80)
print()
print('Refreshing every 10 seconds... Press Ctrl+C to stop')

conn.close()
"
    sleep 10
done
