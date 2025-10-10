# Full-Stack Dating Wizard - Implementation Plan

## 🎯 Goal

Build a **full-stack web application** with:
- **Frontend**: Modern React UI for drag-and-drop image uploads, preference management, and results visualization
- **Backend**: FastAPI REST API serving the classifier
- **Containerization**: Docker + Docker Compose for easy deployment
- **Database**: SQLite for storing preferences, results, and history
- **Deployment**: Single command launch on localhost

## 📋 Detailed Implementation Plan

### Phase 1: Backend API (FastAPI) ⏳

#### 1.1 Create FastAPI Application Structure
**New files**:
- `backend/main.py` - Main FastAPI application
- `backend/api/routes/preferences.py` - Preference management endpoints
- `backend/api/routes/classification.py` - Classification endpoints
- `backend/api/routes/instagram.py` - Instagram search endpoints
- `backend/api/routes/results.py` - Results and history endpoints
- `backend/models/schemas.py` - Pydantic models for API validation
- `backend/database/db.py` - SQLite database setup
- `backend/database/models.py` - SQLAlchemy models
- `backend/services/classifier_service.py` - Wrapper around DatingClassifier
- `backend/config.py` - Configuration management

#### 1.2 API Endpoints to Implement
```
POST   /api/preferences/reference-images     - Upload reference images
DELETE /api/preferences/reference-images/:id - Remove reference image
GET    /api/preferences/reference-images     - List all reference images
PUT    /api/preferences/weights              - Update importance weights
GET    /api/preferences                      - Get all preferences
PUT    /api/preferences                      - Update preferences

POST   /api/classify/screenshot              - Classify single screenshot
POST   /api/classify/batch                   - Classify multiple screenshots
GET    /api/classify/results/:id             - Get classification result

POST   /api/instagram/search                 - Search Instagram profiles
GET    /api/instagram/results                - List search results
GET    /api/instagram/results/:id            - Get specific result

GET    /api/stats/classifier                 - Get classifier statistics
GET    /api/results/history                  - Get classification history
GET    /api/results/matches                  - Get all matches
DELETE /api/results/:id                      - Delete result
```

#### 1.3 File Upload Handling
- Multipart form data for images
- Storage in `uploads/reference_images/`
- Storage in `uploads/screenshots/`
- Thumbnail generation for UI

### Phase 2: Frontend Application (React + TypeScript) ⏳

#### 2.1 Project Structure
**New directory**: `frontend/`
```
frontend/
├── src/
│   ├── components/
│   │   ├── PreferenceSetup/
│   │   │   ├── ReferenceImageUpload.tsx
│   │   │   ├── ImageGallery.tsx
│   │   │   ├── WeightSliders.tsx
│   │   │   └── PreferenceForm.tsx
│   │   ├── Classification/
│   │   │   ├── ScreenshotUpload.tsx
│   │   │   ├── ClassificationResult.tsx
│   │   │   └── ResultsList.tsx
│   │   ├── Instagram/
│   │   │   ├── SearchForm.tsx
│   │   │   ├── ProfileCard.tsx
│   │   │   └── MatchesDashboard.tsx
│   │   ├── Layout/
│   │   │   ├── Navigation.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── Header.tsx
│   │   └── Common/
│   │       ├── DragDropZone.tsx
│   │       ├── ProgressBar.tsx
│   │       └── ScoreDisplay.tsx
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── PreferencesPage.tsx
│   │   ├── ClassifyPage.tsx
│   │   ├── InstagramPage.tsx
│   │   └── HistoryPage.tsx
│   ├── services/
│   │   └── api.ts
│   ├── hooks/
│   │   └── useClassifier.ts
│   ├── types/
│   │   └── index.ts
│   └── App.tsx
├── package.json
└── vite.config.ts
```

#### 2.2 Key UI Features

**Dashboard Page**:
- Overview stats (total matches, accuracy, recent activity)
- Quick actions (upload screenshot, search Instagram)
- Recent matches preview

**Preferences Page**:
- Drag-and-drop reference image upload
- Image gallery with delete functionality
- Weight adjustment sliders (Physical, Personality, Interests)
- Keyword management (add/remove positive/negative)
- Age range selector
- Real-time preference preview

**Classify Page**:
- Drag-and-drop screenshot upload
- Batch upload support
- Real-time classification progress
- Results display with:
  - Match/No Match indicator
  - Confidence percentage
  - Component scores breakdown
  - Reasons list
  - Extracted profile data
- Export results (JSON/CSV)

**Instagram Page**:
- Search form (query, limit, min score)
- Live search progress
- Profile cards with images and bios
- Match indicators
- Click to see full classification details
- Save/bookmark matches

**History Page**:
- Searchable/filterable results table
- Match rate statistics
- Charts/graphs (optional)
- Export capabilities

#### 2.3 UI/UX Design
- **Framework**: React 18 + TypeScript + Vite
- **Styling**: Tailwind CSS
- **Components**: shadcn/ui (modern component library)
- **Icons**: Lucide React
- **Charts**: Recharts (for stats visualization)
- **File Upload**: react-dropzone
- **State Management**: React Query + Zustand
- **Forms**: React Hook Form + Zod validation

### Phase 3: Containerization ⏳

#### 3.1 Docker Configuration
**New files**:
- `Dockerfile.backend` - Backend container
- `Dockerfile.frontend` - Frontend container
- `docker-compose.yml` - Orchestration
- `.dockerignore` - Exclude unnecessary files
- `nginx.conf` - Nginx reverse proxy configuration

#### 3.2 Docker Compose Setup
```yaml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./config:/app/config
      - ./data:/app/data
      - ./uploads:/app/uploads
    environment:
      - DATABASE_URL=sqlite:///app/data/dating_wizard.db

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - backend
      - frontend
```

#### 3.3 One-Command Launch
```bash
docker-compose up -d
# Access at: http://localhost
```

### Phase 4: Database Schema ⏳

#### 4.1 SQLite Tables
```sql
-- Reference Images
reference_images (
    id, file_path, category, description,
    uploaded_at, thumbnail_path
)

-- Preferences
preferences (
    id, physical_weight, personality_weight, interest_weight,
    min_score, super_like_score, age_min, age_max,
    updated_at
)

-- Bio Keywords
bio_keywords (
    id, keyword, type (positive/negative/required)
)

-- Personality Traits
personality_traits (
    id, trait
)

-- Shared Interests
shared_interests (
    id, interest
)

-- Classification Results
classification_results (
    id, screenshot_path, is_match, confidence_score,
    physical_score, personality_score, interest_score,
    name, age, bio, created_at
)

-- Classification Reasons
classification_reasons (
    id, result_id, reason, created_at
)

-- Instagram Searches
instagram_searches (
    id, query, limit, min_score,
    total_found, matches_found, created_at
)

-- Instagram Results
instagram_results (
    id, search_id, username, name, bio, url,
    followers, classification_result_id, created_at
)
```

### Phase 5: Integration & Testing ⏳

#### 5.1 API Integration
- Connect existing DatingClassifier to FastAPI
- Implement background tasks for long-running operations
- WebSocket support for real-time progress updates (optional)

#### 5.2 Testing Files
- `backend/tests/test_api.py` - API endpoint tests
- `frontend/src/tests/` - React component tests
- `tests/integration/test_e2e.py` - End-to-end tests

### Phase 6: Git Integration & CI/CD ⏳

#### 6.1 Git Workflow
**New files**:
- `.github/workflows/docker-build.yml` - GitHub Actions for Docker builds
- `.github/workflows/tests.yml` - Automated testing
- `.gitignore` - Updated for new structure

#### 6.2 Commit Strategy
After each major component:
1. Backend API complete → Commit & Push
2. Frontend complete → Commit & Push
3. Docker setup complete → Commit & Push
4. Integration complete → Commit & Push
5. Documentation complete → Commit & Push

### Phase 7: Documentation ⏳

#### 7.1 New Documentation Files
- `DEPLOYMENT.md` - Deployment instructions
- `API_DOCUMENTATION.md` - API endpoint reference
- `FRONTEND_GUIDE.md` - Frontend development guide
- `DOCKER_GUIDE.md` - Docker setup and troubleshooting
- Update `README.md` with new architecture

#### 7.2 API Documentation
- OpenAPI/Swagger auto-generated docs at `/docs`
- ReDoc at `/redoc`

## 🎨 UI Mockup Description

### Dashboard View
```
┌─────────────────────────────────────────────────────────────┐
│  🧙‍♂️ Dating Wizard                          [Settings] [Help] │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  📊 Overview                                                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │  Total       │ │  Match Rate  │ │  Accuracy    │        │
│  │  Analyzed    │ │              │ │              │        │
│  │     143      │ │    37%       │ │    82%       │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
│                                                               │
│  🎯 Quick Actions                                            │
│  ┌─────────────────────┐  ┌─────────────────────┐          │
│  │  📸 Classify         │  │  🔍 Search           │          │
│  │  Screenshot          │  │  Instagram           │          │
│  └─────────────────────┘  └─────────────────────┘          │
│                                                               │
│  🌟 Recent Matches                                           │
│  ┌───────────────────────────────────────────────┐          │
│  │ Sarah, 28    85% ✅ │ Emma, 26     78% ✅    │          │
│  │ Lisa, 30     72% ✅ │ Mia, 27      91% ✅    │          │
│  └───────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

### Preferences Page
```
┌─────────────────────────────────────────────────────────────┐
│  ⚙️ Preferences                                              │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  📸 Reference Images (Drag & Drop)                           │
│  ┌───────────────────────────────────────────────────────┐  │
│  │   [Drag images here or click to upload]               │  │
│  │                                                         │  │
│  │   [img] [img] [img] [img] [img]                       │  │
│  │   [img] [img] [img] [img] [img]                       │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  ⚖️ Importance Weights                                       │
│  Physical       [━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━] 60%      │
│  Personality    [━━━━━━━━━━━━━━━━━━━] 30%                   │
│  Interests      [━━━━━━] 10%                                 │
│                                                               │
│  📝 Personality Traits                                       │
│  [adventurous] [health-conscious] [+ Add trait]             │
│                                                               │
│  🎨 Shared Interests                                         │
│  [hiking] [yoga] [reading] [+ Add interest]                 │
│                                                               │
│  🔞 Age Range                                                │
│  Min: [25] ━━━━━━━━ Max: [35]                               │
│                                                               │
│  [Save Preferences] [Reset to Default]                       │
└─────────────────────────────────────────────────────────────┘
```

### Classification Page
```
┌─────────────────────────────────────────────────────────────┐
│  📸 Classify Profiles                                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Upload Screenshot(s)                                        │
│  ┌───────────────────────────────────────────────────────┐  │
│  │   [Drag screenshots here or click to upload]          │  │
│  │   Supports: PNG, JPG, JPEG                             │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  Results                                                      │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  ✅ MATCH (85%)                                        │  │
│  │  ┌────────┐  Sarah, 28                                │  │
│  │  │ [IMG]  │  Physical: 90% | Personality: 80% |       │  │
│  │  │        │  Interests: 65%                            │  │
│  │  └────────┘                                            │  │
│  │  💡 Reasons:                                           │  │
│  │  • Strong visual similarity to references             │  │
│  │  • Shares your interest in hiking                     │  │
│  │  • Age within preferred range                         │  │
│  │  [View Details] [Save] [Delete]                       │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  [Export Results] [Clear All]                                │
└─────────────────────────────────────────────────────────────┘
```

## 📦 Technology Stack Summary

### Backend
- **Framework**: FastAPI (async, fast, auto-docs)
- **Database**: SQLAlchemy + SQLite
- **Validation**: Pydantic v2
- **File Storage**: Local filesystem with thumbnails
- **ML**: Existing DatingClassifier (PyTorch, ResNet50)

### Frontend
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite (fast dev server)
- **Styling**: Tailwind CSS
- **Components**: shadcn/ui
- **HTTP Client**: Axios + React Query
- **State**: Zustand (lightweight Redux alternative)
- **Routing**: React Router v6

### DevOps
- **Containerization**: Docker + Docker Compose
- **Reverse Proxy**: Nginx
- **CI/CD**: GitHub Actions
- **Version Control**: Git

## 📁 New Project Structure

```
DatingWizard/
├── backend/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── preferences.py
│   │   │   ├── classification.py
│   │   │   ├── instagram.py
│   │   │   └── results.py
│   │   └── dependencies.py
│   ├── database/
│   │   ├── db.py
│   │   └── models.py
│   ├── models/
│   │   └── schemas.py
│   ├── services/
│   │   └── classifier_service.py
│   ├── main.py
│   ├── config.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── types/
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.frontend
├── nginx.conf
├── DEPLOYMENT.md
├── API_DOCUMENTATION.md
└── [existing files...]
```

## 🚀 Deployment Flow

1. **Development**:
   ```bash
   # Backend
   cd backend && uvicorn main:app --reload

   # Frontend
   cd frontend && npm run dev
   ```

2. **Production (Docker)**:
   ```bash
   docker-compose up --build
   # Access at http://localhost
   ```

## ⏱️ Estimated Timeline

- **Backend API**: 4-6 hours
- **Frontend UI**: 6-8 hours
- **Docker Setup**: 2-3 hours
- **Integration & Testing**: 2-3 hours
- **Documentation**: 1-2 hours

**Total**: ~15-22 hours for complete full-stack application

## 🔄 Git Commit Strategy

Will commit and push after each major milestone:

1. ✅ Backend API foundation (routes, models, database)
2. ✅ Backend services integration (classifier wrapper)
3. ✅ Frontend structure and components
4. ✅ Frontend pages and routing
5. ✅ Docker containerization
6. ✅ Integration and testing
7. ✅ Documentation updates
8. ✅ Final polish and README update

Each commit will have descriptive messages following conventional commits:
- `feat: add preference management API endpoints`
- `feat: implement drag-and-drop image upload UI`
- `docker: add multi-stage builds for production`
- `docs: add deployment guide`

## 🎯 Success Criteria

✅ Single command deployment (`docker-compose up`)
✅ Web UI accessible at `http://localhost`
✅ Drag-and-drop image upload works
✅ Text-based preference management
✅ Real-time classification with progress
✅ Instagram search integration
✅ Results history and export
✅ Mobile-responsive design
✅ Complete API documentation
✅ All changes committed and pushed to GitHub

## 📊 Progress Tracker

### Phase 1: Backend API
- [ ] Create FastAPI project structure
- [ ] Database models and migrations
- [ ] Preference management endpoints
- [ ] Classification endpoints
- [ ] Instagram search endpoints
- [ ] Results history endpoints
- [ ] File upload handling
- [ ] Classifier service integration
- [ ] API documentation (Swagger)
- [ ] Commit & Push: Backend API

### Phase 2: Frontend
- [ ] Initialize React + TypeScript + Vite project
- [ ] Setup Tailwind CSS & shadcn/ui
- [ ] Create Layout components (Navigation, Header)
- [ ] Dashboard page
- [ ] Preferences page with drag-drop
- [ ] Classification page
- [ ] Instagram search page
- [ ] History page
- [ ] API integration (Axios + React Query)
- [ ] Commit & Push: Frontend

### Phase 3: Docker & Deployment
- [ ] Backend Dockerfile
- [ ] Frontend Dockerfile
- [ ] docker-compose.yml
- [ ] Nginx configuration
- [ ] .dockerignore files
- [ ] Test deployment
- [ ] Commit & Push: Docker setup

### Phase 4: Integration & Testing
- [ ] End-to-end testing
- [ ] Bug fixes
- [ ] Performance optimization
- [ ] Commit & Push: Integration

### Phase 5: Documentation
- [ ] DEPLOYMENT.md
- [ ] API_DOCUMENTATION.md
- [ ] FRONTEND_GUIDE.md
- [ ] Update README.md
- [ ] Commit & Push: Documentation

### Phase 6: Final Polish
- [ ] Code cleanup
- [ ] Final testing
- [ ] Commit & Push: Final release
