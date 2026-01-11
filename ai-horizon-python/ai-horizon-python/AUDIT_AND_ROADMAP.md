# AI Horizon - Implementation Audit & Production Roadmap

## Current Status: Working Prototype

**Date**: January 7, 2026
**Version**: 1.0.0-prototype

---

## Part 1: Implementation Audit

### Working Features

| Feature | Status | Notes |
|---------|--------|-------|
| `/api/health` | Working | Health check endpoint |
| `/api/chat` | Working | RAG-powered chat with Gemini File Search |
| `/api/submit` | Working | Submit URLs/content for classification |
| `/api/upload` | Working | Upload PDF/DOCX/TXT files |
| `/api/search` | Working | Search DCWF tasks (GET & POST) |
| `/api/roles` | Working | List DCWF work roles |
| `/api/stats` | Working | Dashboard statistics with new metadata |
| `/api/skills` | Working | Role-based learning paths |
| `/api/resources` | Working | List resources with filters |
| `/api/evidence/{task_id}` | Working | Get evidence for a task |
| Static UI serving | Working | FastAPI serves index.html |
| Local RAG (evidence_store.json) | Working | JSON-based evidence persistence |
| API key rotation | Working | Rotates on rate limit (3 keys) |
| Auto resource tagging | Working | Detects type/difficulty from content |

### Issues Found & Fixed

1. **Evidence Store Not Persisting** - Fixed
   - Problem: `add_to_evidence_store()` was being called but file wasn't written
   - Root cause: Multiple stale uvicorn processes on port 8000
   - Fix: Added atomic writes (`fsync` + temp file rename), better error logging

2. **Stale Server Processes** - User Action Required
   - Multiple uvicorn processes accumulate on port 8000
   - Recommend: Kill all Python processes before starting server
   - Or: Use different port (8001) for fresh instance

3. **Stats Endpoint Missing Fields** - Fixed
   - Old response didn't include `total_resources`, `free_resources`, `resource_types`, `difficulty_levels`
   - Now returns full statistics from evidence store

### Current Bugs/Limitations

| Issue | Severity | Description |
|-------|----------|-------------|
| YouTube extraction unreliable | Medium | Depends on `yt-dlp` which can fail |
| TikTok not supported | Low | Dumpling API key present but not integrated |
| No authentication | High | Anyone can submit/access data |
| In-memory session storage | Medium | Sessions lost on restart |
| No rate limiting on endpoints | Medium | Could be abused |
| Search uses Gemini (slow) | Low | Could use local search for cached data |
| Excel files not supported | Low | Returns error message |

---

## Part 2: Feature Gap Analysis (vs theaihorizon.org)

### Missing Features from Reference Site

| Feature | Priority | Effort | Description |
|---------|----------|--------|-------------|
| User accounts | High | Large | Login, registration, profile |
| Learning paths | Medium | Medium | Structured course sequences |
| Quiz generation | Medium | Medium | AI-generated assessments |
| Chat-with-context | Medium | Small | Chat about specific resource |
| Progress tracking | Medium | Medium | Track completed resources |
| Bookmarks/Favorites | Low | Small | Save resources for later |
| Export data | Low | Small | Download as CSV/JSON |
| Admin dashboard | High | Large | Manage content, users, analytics |
| Resource ratings | Low | Small | User ratings/reviews |
| Mobile responsiveness | Medium | Medium | Better mobile UI |

### UI/UX Improvements Implemented

- Stats dashboard with gradient styling
- Resource type badges (Video, Course, Certification, etc.)
- Difficulty level badges (color-coded)
- Free/Premium indicators
- Skills/Roles navigation tab
- Category filtering
- "Ask AI" buttons on skill cards

---

## Part 3: Production Framework Recommendation

### Recommended Tech Stack

#### Option A: Full-Stack Python (Recommended for your team)

**Framework**: FastAPI + Next.js/React frontend

```
Backend (Keep current):
├── FastAPI (already using)
├── Pydantic (already using)
├── Gemini API (already using)
├── SQLAlchemy + PostgreSQL (add for production)
├── Redis (add for sessions/caching)
├── Celery (add for background tasks)
└── Docker (containerization)

Frontend (Upgrade):
├── Next.js 14+ (React framework)
├── Tailwind CSS (already similar styling)
├── shadcn/ui (component library)
├── React Query (data fetching)
├── Zustand (state management)
└── NextAuth.js (authentication)
```

#### Option B: Keep Simple (Faster to deploy)

```
Current Stack + Enhancements:
├── FastAPI (keep)
├── Jinja2 templates (replace static HTML)
├── HTMX (progressive enhancement)
├── SQLite → PostgreSQL (upgrade)
├── File-based sessions → Redis
└── Render/Railway (easy deployment)
```

### Database Schema for Production

```sql
-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),
    role VARCHAR(50) DEFAULT 'student', -- student, educator, admin
    created_at TIMESTAMP DEFAULT NOW()
);

-- Resources (artifacts)
CREATE TABLE resources (
    id UUID PRIMARY KEY,
    title VARCHAR(500),
    content TEXT,
    source_url VARCHAR(1000),
    source_type VARCHAR(50),
    resource_type VARCHAR(50),
    difficulty VARCHAR(50),
    is_free BOOLEAN DEFAULT TRUE,
    classification VARCHAR(50),
    confidence FLOAT,
    rationale TEXT,
    dcwf_tasks JSONB,
    work_roles JSONB,
    key_findings JSONB,
    ai_tools_mentioned JSONB,
    submitted_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- User progress
CREATE TABLE user_progress (
    user_id UUID REFERENCES users(id),
    resource_id UUID REFERENCES resources(id),
    status VARCHAR(50), -- started, completed
    quiz_score FLOAT,
    completed_at TIMESTAMP,
    PRIMARY KEY (user_id, resource_id)
);

-- Quizzes
CREATE TABLE quizzes (
    id UUID PRIMARY KEY,
    resource_id UUID REFERENCES resources(id),
    questions JSONB,
    generated_at TIMESTAMP DEFAULT NOW()
);
```

### Deployment Options

| Platform | Cost | Difficulty | Features |
|----------|------|------------|----------|
| **Render** | Free tier available | Easy | Managed PostgreSQL, Redis, auto-deploy |
| **Railway** | ~$5/mo | Easy | Similar to Render, great DX |
| **Vercel + Supabase** | Free tier | Medium | Best for Next.js + PostgreSQL |
| **AWS (ECS/Lambda)** | ~$20/mo | Hard | Full control, scalable |
| **DigitalOcean App Platform** | ~$12/mo | Medium | Good balance of control/simplicity |

### Recommended: Render or Railway

1. **Free PostgreSQL** - 1GB database
2. **Auto-deploy from GitHub** - Push to deploy
3. **Managed SSL** - HTTPS automatic
4. **Environment variables** - Secure secrets
5. **Logs and monitoring** - Built-in

---

## Part 4: Implementation Phases

### Phase 1: Stabilization (1-2 weeks)
- [ ] Add proper error handling for all endpoints
- [ ] Add input validation with Pydantic
- [ ] Add request logging
- [ ] Add rate limiting (slowapi)
- [ ] Fix YouTube extraction reliability
- [ ] Add basic authentication (API keys)

### Phase 2: Database Migration (1-2 weeks)
- [ ] Set up PostgreSQL (Supabase or managed)
- [ ] Create SQLAlchemy models
- [ ] Migrate evidence_store.json to database
- [ ] Add Redis for sessions
- [ ] Add Celery for background classification

### Phase 3: Authentication (1 week)
- [ ] Add user registration/login
- [ ] Role-based access (student, educator, admin)
- [ ] Session management
- [ ] Password reset flow

### Phase 4: Enhanced UI (2-3 weeks)
- [ ] Replace static HTML with React/Next.js
- [ ] Add proper routing
- [ ] Add user dashboard
- [ ] Add progress tracking
- [ ] Add quiz feature
- [ ] Mobile responsive design

### Phase 5: Production Deployment (1 week)
- [ ] Set up CI/CD pipeline
- [ ] Configure production environment
- [ ] Set up monitoring (Sentry, Datadog)
- [ ] Load testing
- [ ] Security audit

---

## Part 5: Immediate Next Steps

### Quick Wins (Today)

1. **Kill stale processes**: `taskkill /F /IM python.exe` before starting
2. **Use port 8001**: Avoid conflicts with zombie processes
3. **Test UI at http://localhost:8001**: Verify Skills tab works

### This Week

1. Add rate limiting with `slowapi`
2. Add API key authentication for sensitive endpoints
3. Create requirements.txt with pinned versions
4. Add pytest tests for endpoints
5. Create Dockerfile for consistent deployment

### Code to Add Rate Limiting

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/submit")
@limiter.limit("10/minute")
async def submit_artifact(request: Request, ...):
    ...
```

### Code to Add API Key Auth

```python
from fastapi.security import APIKeyHeader
from fastapi import Security, HTTPException

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != os.getenv("ADMIN_API_KEY"):
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return api_key

@app.delete("/api/resources/{artifact_id}")
async def delete_resource(artifact_id: str, api_key: str = Depends(verify_api_key)):
    ...
```

---

## Summary

The current prototype is functional and demonstrates the core classification pipeline. For production:

1. **Keep FastAPI backend** - It's working well
2. **Add PostgreSQL + Redis** - For proper data persistence
3. **Build React/Next.js frontend** - For better UX
4. **Deploy on Render/Railway** - Easy and affordable
5. **Add authentication** - Required for multi-user

Estimated timeline: **4-6 weeks** for production-ready version.
