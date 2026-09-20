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

Using the **Department of Defense Cyber Workforce Framework (DCWF)**, the project maps evidence against **1,350 tasks** across **52 work roles** to assess how AI may affect cybersecurity work. DCWF and the NICE Workforce Framework are related frameworks, not interchangeable names.

| Classification | Description |
| --- | --- |
| **Replace** | Evidence suggests AI can automate the task |
| **Augment** | AI supports a person performing the task |
| **Remain Human** | Human judgment, accountability, or interaction remains central |
| **New Task** | AI creates new responsibilities |

These are research classifications, not guarantees about job replacement.

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

### Submit Evidence and Learning Resources
Submit articles, papers, PDFs, documents, or YouTube videos for classification and mapping to DCWF tasks. Learning resources can also be categorized by task and work role.

### Feed Ingestion and Video Extraction
The Python backend includes RSS/Atom discovery with normalization and deduplication. YouTube extraction tries direct transcripts, an optional configured proxy, then Gemini video transcription. Dumpling AI was removed from the current backend.

## Repository scope

This public repository contains the **Python backend, ingestion pipeline, DCWF reference data, and legacy static UI**. The Next.js application lives in the separate, private [`ai-horizon-frontend`](https://github.com/Bighabz/ai-horizon-frontend) repository; it is no longer a subdirectory of this repository.

The latest backend fixes include YouTube transcription fallbacks, protected File Search administration, submission error reporting, request timeouts, and log-level normalization. The setup below matches the `master` branch.

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
- Python 3.11+ for this backend
- Node.js 20.9+ if you have access to the separate Next.js frontend
- Google Gemini API key
- Optional: a PostgreSQL database (Railway provides one in production via
  `DATABASE_URL`; local dev works without it using the JSON fallback)

### Frontend (separate private repository)

Repository access is required. The public backend also provides a legacy static interface at `/`, so the private frontend is not required to inspect or run the backend.

```bash
git clone https://github.com/Bighabz/ai-horizon-frontend.git
cd ai-horizon-frontend
npm install
cp .env.example .env.local
# Add your environment variables
npm run dev
```

### Backend

```bash
git clone https://github.com/Bighabz/AI-Horizon.git
cd AI-Horizon/ai-horizon-python/ai-horizon-python
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Fill in GEMINI_API_KEY (required). DATABASE_URL, ADMIN_API_KEY, and the
# File Search store names enable their corresponding RAG features.
# Leave DATABASE_URL empty to use the local JSON evidence fallback.
# See .env.example for the full list with comments.
uvicorn src.api.main:app --reload --port 8005
```

Key environment variables (full reference in `ai-horizon-python/ai-horizon-python/.env.example`):

| Variable | Required | Purpose |
|---|---|---|
| `GEMINI_API_KEY` (+`_2`, `_3`) | Yes | Gemini classification/chat (extra keys rotate on rate limits) |
| `DATABASE_URL` | Prod | Railway PostgreSQL (injected by Railway; JSON fallback if absent) |
| `DCWF_STORE_NAME`, `EVIDENCE_STORE_NAME`, `RESOURCES_STORE_NAME` | Prod | Gemini File Search stores for RAG |
| `ADMIN_API_KEY` | Prod | Protects admin endpoints |
| `YOUTUBE_API_KEY` | No | Optional YouTube metadata support |
| `WEBSHARE_PROXY_USERNAME`, `WEBSHARE_PROXY_PASSWORD` or `YT_PROXY_URL` | No | Optional proxy for transcript retrieval |
| `YT_GEMINI_FALLBACK` | No | Enable/disable Gemini video transcription fallback |
| `LOG_LEVEL` | No | Application logging level |

In production, set all secrets as Railway environment variables — never commit `.env`.

See [DEPLOYMENT.md](DEPLOYMENT.md) for the current API paths and deployment layout, and the [backend README](ai-horizon-python/ai-horizon-python/README.md) for CLI commands and feed ingestion.

### Offline tests

```bash
cd ai-horizon-python/ai-horizon-python  # from the repository root
python -m pytest tests/ -q
```

## Research

This project is part of ongoing research into workforce development in the age of AI. Our methodology includes:

1. **DCWF Mapping**: Evidence and learning resources are mapped to DoD cybersecurity tasks and work roles
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
