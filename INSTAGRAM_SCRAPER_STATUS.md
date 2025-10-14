# Instagram Scraper Implementation Status

## 🎯 Current Progress

### ✅ Completed

1. **Database Schema** (100%)
   - Added 10 columns to `instagram_results` table
   - Supports screenshots, CLIP embeddings, scores, feedback
   - Migration script: `backend/migrations/add_instagram_embeddings.py`
   - Ready for automated scraping pipeline

2. **Training Data Infrastructure** (100%)
   - Embedding storage system working
   - 8/9 profiles with embeddings + feedback
   - Progress: 8/50 (16%) toward training threshold

3. **Existing Scrapers** (100%)
   - Instagram scraper: `src/scrapers/instagram_scraper.py`
   - Google Images scraper: `src/scrapers/google_images_scraper.py`
   - Both ready to integrate

### 🚧 In Progress

**Next Implementation Steps:**

#### 1. Update SQLAlchemy Model (30 min)
```python
# backend/database/models.py - InstagramResult class
# Add new columns to match database schema
```

#### 2. Create Instagram Service (2 hours)
```python
# backend/services/instagram_service.py

class InstagramScrapingService:
    def scrape_profile(username) -> InstagramResult:
        # 1. Screenshot profile using existing scraper
        # 2. Classify with CLIP
        # 3. Extract embedding
        # 4. Store in instagram_results

    def start_hashtag_search(hashtags, limit):
        # Queue background scraping job
        # Return job_id for status tracking
```

#### 3. API Endpoints (1 hour)
```python
# backend/api/routes/instagram.py

POST   /api/instagram/scrape/profile     # Single profile
POST   /api/instagram/scrape/hashtag     # Hashtag search
GET    /api/instagram/results            # View results
POST   /api/instagram/results/{id}/feedback  # Rate profile
```

#### 4. Frontend UI (2 hours)
```typescript
// frontend/src/pages/InstagramScraperPage.tsx

- Hashtag input field
- "Start Scraping" button
- Progress display (real-time)
- Results grid with Like/Dislike buttons
```

---

## 🎬 Automated Scraping Strategy

### **Conservative Rate Limiting** (Approved)

```python
DELAYS = {
    "between_profiles": (300, 480),      # 5-8 minutes
    "between_hashtags": (60, 120),       # 1-2 minutes
    "long_pause_every": 20,              # profiles
    "long_pause_duration": (3600, 5400)  # 1-1.5 hours
}
```

### **Expected Timeline**

```
Input: 3 hashtags × 20 profiles = 60 profiles
Timeline: 10 hours (overnight run)
Risk: 3/10 (very low with conservative limits)
Result: 50+ profiles → Hit training threshold!
```

### **Workflow**

```
1. User enters hashtags: ["photography", "model", "fashion"]
2. Click "Start Scraping"
3. Backend:
   - Searches each hashtag → extracts usernames
   - Visits profiles (1 every 5-8 min)
   - Screenshots + CLIP classification
   - Stores with embeddings
4. Next morning:
   - View 60 ranked results
   - Rate top profiles (30 min)
   - Hit 50+ training threshold!
5. Train first model
```

---

## 📋 Implementation Checklist

### Phase 1: Backend (3-4 hours)
- [ ] Update InstagramResult SQLAlchemy model
- [ ] Create Instagram service class
- [ ] Integrate existing scraper code
- [ ] Add CLIP classification
- [ ] Add embedding extraction
- [ ] Create API endpoints
- [ ] Add request validation

### Phase 2: Frontend (2-3 hours)
- [ ] Create Instagram scraper page
- [ ] Hashtag input component
- [ ] Start/stop scraping controls
- [ ] Real-time progress display
- [ ] Results grid component
- [ ] Feedback buttons (Like/Dislike/Super Like)
- [ ] Filter by score threshold

### Phase 3: Testing (1 hour)
- [ ] Test single profile scrape
- [ ] Test hashtag search (5 profiles)
- [ ] Verify CLIP classification
- [ ] Verify embedding storage
- [ ] Test feedback submission
- [ ] Verify database integrity

### Phase 4: Production Run (10 hours)
- [ ] Start overnight scrape (60 profiles)
- [ ] Monitor for errors
- [ ] Review results next morning
- [ ] Rate all profiles
- [ ] Reach 50+ training threshold

---

## 🚨 Risk Mitigation

### Instagram Detection Avoidance

**Conservative Approach:**
- ✅ 5-8 minute delays (humans browse slower!)
- ✅ Random timing variations
- ✅ Long pauses every 20 profiles
- ✅ Nighttime running (normal hours)
- ✅ Use logged-in browser profile
- ✅ Limit to 60 profiles total (not 1000s)

**If Soft-Banned:**
- Wait 24 hours
- Resume at slower rate (10 min delays)
- No permanent consequences

### Alternatives if Needed

1. **Manual username collection**
   - You browse Instagram, copy usernames
   - App screenshots them slowly
   - Zero risk

2. **Google Images fallback**
   - No bans possible
   - 300 images in 1 hour
   - But no bio text (personality scoring disabled)

---

## 📊 Current Training Dataset

```
Total feedback: 9 profiles
With embeddings: 8/9 (89%)

Breakdown:
├─ super_like: 6 ⭐⭐⭐
├─ like: 2 👍
└─ dislike: 1

Progress: 8/50 (16%)
Needed: 42 more for first training
```

---

## 🎯 Success Metrics

### Short-term (This Week)
- [ ] 50+ profiles with feedback
- [ ] All with CLIP embeddings stored
- [ ] Ready for first model training

### Medium-term (Next 2 Weeks)
- [ ] 100+ profiles collected
- [ ] First model trained and deployed
- [ ] Improved classification accuracy

### Long-term (Month 1-2)
- [ ] 200+ profiles
- [ ] CLIP fine-tuned on your preferences
- [ ] 85%+ accuracy on matches

---

## 🚀 Next Session Plan

**Priority 1: Complete Backend Service (2-3 hours)**
1. Update SQLAlchemy model
2. Create Instagram service
3. Build API endpoints
4. Test with 1 profile manually

**Priority 2: Build Frontend UI (2 hours)**
1. Create scraper page
2. Add hashtag input
3. Display results grid
4. Add feedback buttons

**Priority 3: Test & Deploy (1 hour)**
1. Test with 5 profiles
2. Fix any bugs
3. Start overnight scrape for 60 profiles

**Next Morning: Review & Rate**
1. Review 60 scraped profiles (10 min)
2. Rate top 50 matches (30 min)
3. Hit training threshold!
4. Train first model 🎉

---

## 📁 File Structure

```
backend/
├── migrations/
│   ├── add_embeddings_column.py ✅
│   ├── add_instagram_embeddings.py ✅
│   └── backfill_embeddings.py ✅
├── services/
│   ├── classifier_service.py ✅
│   └── instagram_service.py ⏳ NEXT
├── api/routes/
│   ├── classification.py ✅
│   ├── preferences.py ✅
│   ├── results.py ✅
│   └── instagram.py ⏳ NEXT
└── database/
    └── models.py ⏳ UPDATE NEEDED

src/scrapers/
├── instagram_scraper.py ✅
├── google_images_scraper.py ✅
└── base_scraper.py ✅

frontend/src/pages/
├── ClassifyPage.tsx ✅
├── PreferencesPage.tsx ✅
└── InstagramScraperPage.tsx ⏳ NEXT
```

---

## 💡 Key Decisions Made

1. **Instagram over Google Images**
   - More authentic training data
   - Bio text enables personality scoring
   - Manageable risk with conservative limits

2. **Automated with Conservative Rate Limiting**
   - 5-8 minutes between profiles
   - Long pauses every 20 profiles
   - Overnight runs (10 hours for 60 profiles)

3. **Hybrid Manual + Automated**
   - User provides seed hashtags
   - System automates the tedious work
   - User reviews and rates results

4. **Embedding-First Architecture**
   - Store embeddings immediately
   - Enable fast training later
   - Support similarity search

---

## 📞 Support & References

- **Instagram Scraper Docs**: [INSTAGRAM_SCRAPER.md](./INSTAGRAM_SCRAPER.md)
- **Training Data Flow**: [TRAINING_DATA_FLOW.md](./TRAINING_DATA_FLOW.md)
- **Active Learning Plan**: (check existing docs)
- **Project Plan**: [PROJECT_PLAN.md](./PROJECT_PLAN.md)

---

**Status**: Ready to implement backend service and API endpoints!
**Estimated Completion**: 6-8 hours of development
**Next Milestone**: 50+ profiles for first model training
