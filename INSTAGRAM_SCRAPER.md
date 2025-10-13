# Instagram Scraper Implementation Plan

## Overview
Automated Instagram profile scraper that captures screenshots of profiles and posts, classifies them using CLIP, and allows user feedback for continuous model improvement.

---

## Architecture: Hybrid Approach

### Profile-First with Selective Post Deep-Dive

```
For each Instagram profile:
├─ 1. Screenshot full profile page (bio, profile pic, top posts grid)
├─ 2. Extract bio text with OCR
├─ 3. Run CLIP classification on profile screenshot
├─ 4. If score > threshold (e.g., 0.6):
│   ├─ Extract top 6-9 individual post URLs
│   ├─ Screenshot individual posts (optional deep-dive)
│   └─ Store for detailed review
└─ 5. Store result in database for user feedback
```

### Why Hybrid?
- ✅ **Fast**: Only 1 screenshot per profile for initial classification
- ✅ **Contextual**: CLIP sees complete visual layout (like Tinder)
- ✅ **Scalable**: Can deep-dive into posts for matches
- ✅ **Efficient storage**: Screenshots only promising profiles in detail

---

## Technical Stack

### Browser Automation
- **Selenium** or **Playwright** for headless browsing
- **Chrome/Firefox** in headless mode
- **User agent rotation** to avoid detection

### Image Processing
- **Pillow (PIL)** for screenshot manipulation
- **pytesseract** for bio text extraction (already installed)
- **OpenCV** for image preprocessing (already installed)

### Instagram Libraries (Optional)
- **Instaloader**: Metadata extraction without screenshots
- **Instagram-Private-API**: More control but against ToS

### Existing Infrastructure
- ✅ CLIP classifier already working
- ✅ Database schema exists (`instagram_searches`, `instagram_results`)
- ✅ Feedback system ready

---

## Database Schema

### Current Schema (Already Exists)

```sql
-- Instagram search jobs
CREATE TABLE instagram_searches (
    id INTEGER PRIMARY KEY,
    query TEXT NOT NULL,
    search_type TEXT,  -- 'hashtag', 'location', 'username'
    limit_count INTEGER,
    min_score REAL,
    status TEXT,  -- 'pending', 'running', 'completed', 'failed'
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Individual profile results
CREATE TABLE instagram_results (
    id INTEGER PRIMARY KEY,
    search_id INTEGER,
    username TEXT NOT NULL,
    profile_url TEXT,
    bio TEXT,
    follower_count INTEGER,
    following_count INTEGER,
    post_count INTEGER,
    is_match BOOLEAN,
    confidence_score REAL,

    -- Need to add these:
    screenshot_path TEXT,  -- Full profile screenshot
    profile_pic_path TEXT,  -- Profile picture

    -- CLIP scores
    physical_score REAL,
    personality_score REAL,
    interest_score REAL,

    -- User feedback
    user_feedback TEXT,  -- 'like', 'dislike', 'super_like'
    feedback_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (search_id) REFERENCES instagram_searches(id)
);

-- Individual post screenshots (for deep-dive)
CREATE TABLE instagram_posts (
    id INTEGER PRIMARY KEY,
    result_id INTEGER,
    post_url TEXT NOT NULL,
    screenshot_path TEXT,
    caption TEXT,
    likes_count INTEGER,
    comments_count INTEGER,
    posted_at TIMESTAMP,

    -- CLIP classification
    confidence_score REAL,
    is_match BOOLEAN,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (result_id) REFERENCES instagram_results(id)
);
```

---

## Implementation Phases

### Phase 1: Basic Profile Scraper (MVP)
**Goal**: Screenshot profiles and classify with CLIP

#### Components:
1. **Instagram Profile Scraper** (`src/scrapers/instagram_scraper.py`)
   ```python
   class InstagramProfileScraper:
       def __init__(self, headless=True):
           self.driver = webdriver.Chrome(options=chrome_options)

       def screenshot_profile(self, username: str) -> str:
           """Navigate to profile and capture screenshot"""
           url = f"https://instagram.com/{username}"
           self.driver.get(url)

           # Wait for page load
           # Scroll to capture top posts
           # Take full-page screenshot

           return screenshot_path

       def extract_bio(self, screenshot_path: str) -> str:
           """Use OCR to extract bio text"""
           # Use existing pytesseract
           pass
   ```

2. **Backend API Endpoint** (`backend/api/routes/instagram.py`)
   ```python
   @router.post("/search", response_model=InstagramSearchResponse)
   async def search_instagram(
       query: str,
       limit: int = 20,
       min_score: float = 0.6,
       db: Session = Depends(get_db)
   ):
       # Create search job
       # Run scraper in background
       # Classify profiles with CLIP
       # Return results
   ```

3. **Frontend Search Interface** (`frontend/src/pages/InstagramPage.tsx`)
   - Search input for username/hashtag
   - Results grid with profile screenshots
   - Like/Dislike/Super Like buttons
   - Filter by score

#### Workflow:
```
User Input: @username or #hashtag
    ↓
Scraper: Navigate to Instagram
    ↓
Capture: Full profile screenshot
    ↓
Extract: Bio text with OCR
    ↓
Classify: CLIP model scores profile
    ↓
Store: Screenshot + scores in DB
    ↓
Display: Results to user for feedback
```

---

### Phase 2: Search & Discovery
**Goal**: Find profiles by hashtag, location, or similar

#### Features:
- **Hashtag search**: `#photography` → scrape top posts → extract usernames
- **Location search**: `New York` → scrape tagged posts
- **Similar profiles**: Given a username, find similar profiles
- **Batch processing**: Queue multiple searches

#### Implementation:
```python
class InstagramSearchEngine:
    def search_hashtag(self, hashtag: str, limit: int = 50):
        """Scrape posts by hashtag, extract unique usernames"""
        pass

    def search_location(self, location_id: str, limit: int = 50):
        """Scrape posts by location"""
        pass

    def find_similar(self, username: str, limit: int = 20):
        """Find similar profiles using CLIP embeddings"""
        # Get target profile embedding
        # Compare with database embeddings
        # Return top similar profiles
        pass
```

---

### Phase 3: Post-Level Analysis
**Goal**: Deep-dive into individual posts for high-scoring profiles

#### Features:
- Screenshot top 9-12 posts from profile grid
- Classify each post individually
- Aggregate scores across posts
- Show post gallery in UI

#### Implementation:
```python
def deep_dive_profile(self, username: str, profile_score: float):
    """If profile_score > 0.7, screenshot individual posts"""
    if profile_score < 0.7:
        return  # Skip deep-dive

    # Extract post URLs from profile grid
    post_urls = self.extract_post_urls(username, limit=9)

    for url in post_urls:
        # Screenshot post
        # Classify with CLIP
        # Store in instagram_posts table
        pass
```

---

### Phase 4: Smart Scraping & Anti-Detection

#### Features:
- **Rate limiting**: Random delays between requests (2-5 seconds)
- **Session management**: Reuse browser session
- **User agent rotation**: Avoid bot detection
- **Proxy support**: Rotate IPs if needed
- **Cookies/Login**: Optional Instagram login for more access

#### Implementation:
```python
class SmartScraper:
    def __init__(self):
        self.request_count = 0
        self.last_request_time = None

    def smart_delay(self):
        """Random delay to mimic human behavior"""
        delay = random.uniform(2.0, 5.0)
        time.sleep(delay)

    def should_pause(self):
        """Pause every 50 requests to avoid rate limits"""
        if self.request_count % 50 == 0:
            time.sleep(random.uniform(60, 120))  # 1-2 min pause
```

---

## API Endpoints

### Search Endpoints
```python
POST /api/instagram/search
{
    "query": "@username or #hashtag",
    "search_type": "username" | "hashtag" | "location",
    "limit": 20,
    "min_score": 0.6
}

Response:
{
    "search_id": 1,
    "status": "pending",
    "query": "@natgeo",
    "created_at": "2025-10-13T01:30:00Z"
}

GET /api/instagram/searches/{search_id}
Response:
{
    "id": 1,
    "status": "completed",
    "results_count": 15,
    "matches_count": 8,
    "results": [...]
}

GET /api/instagram/results
Query params: ?search_id=1&matches_only=true
Response: [
    {
        "id": 1,
        "username": "natgeo",
        "screenshot_path": "/uploads/instagram/natgeo_profile.jpg",
        "bio": "Experience the world through...",
        "confidence_score": 0.85,
        "is_match": true,
        "user_feedback": null
    }
]
```

### Feedback Endpoints (Reuse existing)
```python
POST /api/results/{result_id}/feedback
{
    "feedback": "like" | "dislike" | "super_like"
}
```

---

## UI Design

### Instagram Search Page

```
┌─────────────────────────────────────────────┐
│  🔍 Instagram Search                        │
├─────────────────────────────────────────────┤
│                                             │
│  Search: [@username or #hashtag]  [Search] │
│                                             │
│  Filters:                                   │
│  Min Score: [▓▓▓▓▓░░░░░] 60%              │
│  Limit: [20 ▼]                             │
│                                             │
├─────────────────────────────────────────────┤
│  Results (15 profiles, 8 matches)          │
│                                             │
│  ┌───────┐  ┌───────┐  ┌───────┐          │
│  │ 📸    │  │ 📸    │  │ 📸    │          │
│  │Profile│  │Profile│  │Profile│          │
│  │       │  │       │  │       │          │
│  │ ✅ 85%│  │ ✅ 72%│  │ ❌ 45%│          │
│  │[Like] │  │[Like] │  │[Skip] │          │
│  └───────┘  └───────┘  └───────┘          │
│                                             │
└─────────────────────────────────────────────┘
```

---

## Privacy & Legal Considerations

### ⚠️ Important Warnings

1. **Instagram Terms of Service**
   - Automated scraping violates Instagram ToS
   - Risk of account ban or IP block
   - Use at your own risk

2. **Ethical Use**
   - Only for personal, non-commercial use
   - Respect privacy - don't store/share others' content
   - Rate limit to avoid server load

3. **Data Storage**
   - Store screenshots locally only
   - Don't redistribute or sell data
   - Consider adding auto-deletion after N days

### Mitigation Strategies
- Use personal account for login (optional)
- Implement aggressive rate limiting
- Add user consent warnings in UI
- Provide data deletion options

---

## Performance Optimization

### Caching Strategy
```python
# Cache profile screenshots for 7 days
SCREENSHOT_CACHE_TTL = 7 * 24 * 3600

def get_cached_screenshot(username: str) -> Optional[str]:
    """Check if recent screenshot exists"""
    recent = db.query(InstagramResult).filter(
        InstagramResult.username == username,
        InstagramResult.created_at > datetime.now() - timedelta(days=7)
    ).first()

    if recent and os.path.exists(recent.screenshot_path):
        return recent.screenshot_path

    return None
```

### Batch Processing
```python
# Process searches in background queue
from celery import Celery

@celery.task
def process_instagram_search(search_id: int):
    """Background task for scraping"""
    search = db.query(InstagramSearch).get(search_id)
    search.status = 'running'

    # Scrape profiles
    # Classify with CLIP
    # Update database

    search.status = 'completed'
    db.commit()
```

---

## Success Metrics

### Phase 1 MVP Goals
- [ ] Successfully screenshot 100 profiles
- [ ] CLIP classification accuracy > 70%
- [ ] No rate limiting or IP bans
- [ ] User provides feedback on 50+ profiles

### Phase 2 Goals
- [ ] Hashtag search working for top 10 hashtags
- [ ] Find 500+ profiles in database
- [ ] User satisfaction with search results > 80%

### Phase 3 Goals
- [ ] Post-level analysis for 100+ profiles
- [ ] Identify content patterns (e.g., "travel photos score high")
- [ ] Model fine-tuning shows improvement from feedback

---

## Next Steps

1. **Immediate**: Create basic profile scraper
2. **Week 1**: Screenshot 100 profiles, gather feedback
3. **Week 2**: Implement hashtag search
4. **Week 3**: Post-level deep-dive
5. **Month 1**: Full scraping system with smart anti-detection

---

## Related Documentation
- [ACTIVE_LEARNING.md](./ACTIVE_LEARNING.md) - Model training with feedback
- [TRAINING_DATA_FLOW.md](./TRAINING_DATA_FLOW.md) - How embeddings are used
- [PROJECT_PLAN.md](./PROJECT_PLAN.md) - Overall project roadmap
