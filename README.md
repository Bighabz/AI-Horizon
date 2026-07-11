# AI Horizon - Educating into the AI Future

<p align="center">
  <strong>Understanding How AI Transforms Cybersecurity Careers</strong>
</p>

<p align="center">
  <a href="https://theaihorizon.org">Website</a> •
  <a href="#features">Features</a> •
  <a href="#getting-started">Getting Started</a> •
  <a href="#research">Research</a>
</p>

---

## About

**AI Horizon** is an NSF-funded research project at California State University, San Bernardino (CSUSB) that analyzes how artificial intelligence is transforming the cybersecurity workforce.

Using the **NICE Workforce Framework for Cybersecurity (DCWF)**, we classify over **1,350 tasks** across **52 work roles** to determine how AI will impact each one:

| Classification | Description | Confidence |
|---------------|-------------|------------|
| **Replace** | AI can fully automate this task | >70% |
| **Augment** | AI enhances human capabilities | 40-70% |
| **Remain Human** | Requires human judgment/creativity | <40% |
| **New Task** | AI creates entirely new responsibilities | - |

## Features

### Skills Matrix
Explore all DCWF work roles with visual breakdowns of AI impact. Filter by category, role, or classification type.

### Evidence Library
Browse the research papers, articles, and reports that inform our classifications. Every classification is backed by evidence.

### AI Assistant
Chat with our Gemini-powered assistant for personalized career guidance:
- Get analysis of specific roles
- Practice with AI-generated quizzes
- Build career development plans
- Understand skill gaps

### Submit Evidence
Contribute to the research by submitting articles or papers about AI in cybersecurity. Our system automatically classifies and maps them to DCWF tasks.

## Tech Stack

```
Frontend          Backend           Database
─────────         ───────           ────────
Next.js 16        FastAPI           Railway PostgreSQL
Tailwind CSS v4   Gemini AI         (evidence_store.json
shadcn/ui         Python 3.11+       fallback for local dev)
React Query       RAG Pipeline
```

The backend is deployed on **Railway** (auto-deploys from `master`) and uses
**Railway PostgreSQL** as its database (migrated from Supabase in Feb 2026 —
see `ai-horizon-python/ai-horizon-python/src/api/db.py`). When no database is
reachable locally, the API falls back to the JSON evidence store.

## Getting Started

### Prerequisites
- Node.js 18+
- Python 3.11+
- Google Gemini API key
- Optional: a PostgreSQL database (Railway provides one in production via
  `DATABASE_URL`; local dev works without it using the JSON fallback)

### Frontend

```bash
cd ai-horizon-frontend
npm install
cp .env.example .env.local
# Add your environment variables
npm run dev
```

### Backend

```bash
cd ai-horizon-python/ai-horizon-python
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Fill in GEMINI_API_KEY (required). DATABASE_URL, ADMIN_API_KEY, and the
# File Search store names are optional for local development —
# see .env.example for the full list with comments.
uvicorn src.api.main:app --reload --port 8005
```

Key environment variables (full reference in `ai-horizon-python/ai-horizon-python/.env.example`):

| Variable | Required | Purpose |
|---|---|---|
| `GEMINI_API_KEY` (+`_2`, `_3`) | Yes | Gemini classification/chat (extra keys rotate on rate limits) |
| `DATABASE_URL` | Prod | Railway PostgreSQL (injected by Railway; JSON fallback if absent) |
| `DCWF_STORE_NAME`, `EVIDENCE_STORE_NAME`, `RESOURCES_STORE_NAME` | Prod | Gemini File Search stores for RAG |
| `ADMIN_API_KEY` | Prod | Protects admin endpoints |
| `DUMPLING_API_KEY`, `YOUTUBE_API_KEY` | No | Optional extraction fallbacks |

In production, set all secrets as Railway environment variables — never commit `.env`.

## Research

This project is part of ongoing research into workforce development in the age of AI. Our methodology includes:

1. **DCWF Mapping**: Every cybersecurity task is mapped to the NICE framework
2. **Evidence Collection**: Research papers, industry reports, and expert analysis
3. **AI Classification**: Gemini-powered analysis with human verification
4. **Continuous Updates**: Regular re-evaluation as AI capabilities evolve

## Contributing

We welcome contributions! Submit evidence through the web interface or:

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## Acknowledgments

- National Science Foundation (NSF) for funding
- CSUSB School of Computer Science & Engineering
- NICE Workforce Framework for Cybersecurity

---

<p align="center">
  <sub>Built with purpose at California State University, San Bernardino</sub>
</p>
