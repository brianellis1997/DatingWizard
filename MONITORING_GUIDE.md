# Instagram Scraping Monitoring Guide

## Quick Status Check

Run this command to see current progress:

```bash
docker exec dating-wizard-backend python -c "
import sqlite3
from datetime import datetime

conn = sqlite3.connect('data/dating_wizard.db')
cursor = conn.cursor()

cursor.execute('SELECT COUNT(*) FROM instagram_results')
total = cursor.fetchone()[0]

cursor.execute(\"SELECT COUNT(*) FROM instagram_results WHERE created_at >= datetime('now', '-10 minutes')\")
last_10min = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM instagram_results WHERE profile_image_url IS NOT NULL')
with_images = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM instagram_searches')
searches = cursor.fetchone()[0]

print(f'Total profiles: {total} | Last 10min: {last_10min} | With images: {with_images} | Searches: {searches}')

cursor.execute('''
    SELECT username, strftime('%H:%M:%S', created_at, 'localtime')
    FROM instagram_results ORDER BY created_at DESC LIMIT 3
''')
print('Latest 3:')
for username, time in cursor.fetchall():
    print(f'  {time} - {username}')

conn.close()
"
```

## Continuous Monitoring

Run the monitoring script that updates every 10 seconds:

```bash
./scripts/monitor_instagram.sh
```

Press `Ctrl+C` to stop.

## Check Backend Logs

### View all Instagram-related logs:
```bash
docker logs dating-wizard-backend 2>&1 | grep -i instagram
```

### Follow logs in real-time:
```bash
docker logs -f dating-wizard-backend
```

### Filter for errors only:
```bash
docker logs dating-wizard-backend 2>&1 | grep -E "(ERROR|WARNING|login wall)"
```

## Check Screenshots

### List all Instagram screenshots:
```bash
docker exec dating-wizard-backend ls -lh uploads/screenshots/instagram/
```

### Count screenshots:
```bash
docker exec dating-wizard-backend ls uploads/screenshots/instagram/ | wc -l
```

### View login wall screenshots (if Instagram is blocking):
```bash
docker exec dating-wizard-backend ls uploads/screenshots/instagram/ | grep LOGIN_WALL
```

## Database Queries

### Check profile counts by feedback type:
```bash
docker exec dating-wizard-backend python -c "
import sqlite3
conn = sqlite3.connect('data/dating_wizard.db')
cursor = conn.cursor()

cursor.execute('SELECT user_feedback, COUNT(*) FROM instagram_results WHERE user_feedback IS NOT NULL GROUP BY user_feedback')
for feedback, count in cursor.fetchall():
    print(f'{feedback}: {count}')

conn.close()
"
```

### Check scraping rate (profiles per hour):
```bash
docker exec dating-wizard-backend python -c "
import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('data/dating_wizard.db')
cursor = conn.cursor()

cursor.execute(\"SELECT COUNT(*) FROM instagram_results WHERE created_at >= datetime('now', '-1 hour')\")
last_hour = cursor.fetchone()[0]

print(f'Profiles scraped in last hour: {last_hour}')
print(f'Estimated rate: {last_hour} profiles/hour')
print(f'Estimated for 20 profiles: {20/last_hour if last_hour > 0 else 0:.1f} hours remaining')

conn.close()
"
```

## Understanding the Output

### Status Dashboard:
- **Total profiles**: All-time scraped count
- **Last hour/10min**: Recent activity indicator
- **With profile images**: Success rate (Instagram not blocking)
- **With screenshots**: Should be 100% if scraper is working
- **With embeddings**: Should be 100% for CLIP classification
- **With feedback**: User-rated profiles

### Profile Table Columns:
- **Username**: Instagram username
- **Score**: Physical attractiveness score (0-1)
- **Feedback**: User rating (like/dislike/super_like/pending)
- **Img**: ✓ if profile image extracted, ✗ if login wall
- **Scrn**: ✓ if screenshot saved
- **Time**: When profile was scraped

## Troubleshooting

### No new profiles appearing:
1. Check if scraping is running in UI
2. Check backend logs for errors: `docker logs dating-wizard-backend | tail -50`
3. Look for "login wall" messages indicating Instagram blocking

### Profile images missing (✗ in Img column):
- Instagram is showing login wall
- Check [INSTAGRAM_SCRAPER_STATUS.md](INSTAGRAM_SCRAPER_STATUS.md) for solutions
- Screenshots will still be captured showing the login page

### Slow scraping rate:
- Normal: 1-2 profiles every 5-8 minutes (anti-detection delays)
- If completely stalled: Check logs for errors or restart Docker

### Database connection errors:
```bash
# Restart backend container
docker-compose restart backend
```

## Expected Timeline

For scraping 20 profiles with conservative delays:

- **Rate**: ~1 profile every 5-8 minutes
- **Total time**: 2-3 hours
- **Success**: If profile images are being extracted (no login wall)
- **Partial success**: If only screenshots captured (login wall active)

## Next Steps After Scraping

Once you have 20+ profiles scraped:

1. **Check total count**: Run quick status check
2. **Review results**: Visit [http://localhost/instagram-scraper](http://localhost/instagram-scraper)
3. **Rate profiles**: Add feedback to build training dataset
4. **Monitor success rate**: Check how many have profile images vs login wall

## Commands Reference

```bash
# Quick status
docker exec dating-wizard-backend python -c "import sqlite3; c = sqlite3.connect('data/dating_wizard.db').cursor(); c.execute('SELECT COUNT(*) FROM instagram_results'); print(f'Total: {c.fetchone()[0]}')"

# Continuous monitoring
./scripts/monitor_instagram.sh

# Real-time logs
docker logs -f dating-wizard-backend

# Screenshot count
docker exec dating-wizard-backend ls uploads/screenshots/instagram/ | wc -l

# Check for Instagram blocking
docker logs dating-wizard-backend 2>&1 | grep -i "login wall"
```
