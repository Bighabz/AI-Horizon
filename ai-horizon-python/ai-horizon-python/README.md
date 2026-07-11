# AI Horizon - Python RAG Pipeline

An AI-powered classification system for analyzing how artificial intelligence impacts the cybersecurity workforce, built on the DCWF (Department of Defense Cyber Workforce Framework).

## Project Background

This is an NSF-funded research project at California State University San Bernardino, led by Dr. Vincent Nestler. The goal is to collect and classify "social proof" artifacts that demonstrate AI's impact on cybersecurity jobs.

## Features

- **FastAPI web API**: chat, search, submit, upload, stats endpoints consumed by the Next.js frontend
- **Multi-format extraction**: PDF, DOCX, YouTube, web articles
- **AI Classification**: Categorize artifacts as Replace, Augment, Remain Human, or New Task
- **DCWF Mapping**: Link artifacts to specific cybersecurity workforce tasks
- **RAG-powered queries**: Ask questions about your classified artifacts
- **Feed ingestion**: Pull new evidence candidates from cybersecurity RSS/Atom feeds (`src/ingestion/`)

## Tech Stack

- **Python 3.11+**
- **FastAPI + Uvicorn** (web API, deployed on Railway)
- **Railway PostgreSQL** (`document_registry` table via psycopg2; migrated from
  Supabase in Feb 2026 — see `src/api/db.py`. Falls back to `evidence_store.json`
  when no database is reachable, e.g. local dev)
- **Google Gemini API** (2.5 Flash/Pro, multi-key rotation)
- **Gemini File Search** (Managed RAG)
- **Typer** (CLI framework)
- **Pydantic** (Data validation)
- **slowapi** (rate limiting)

## Quick Start

```bash
# Clone and setup
git clone <repo>
cd ai-horizon-python/ai-horizon-python
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Fill in GEMINI_API_KEY (required); see .env.example for all keys.
# DATABASE_URL is optional locally - without it the API uses evidence_store.json.

# Run the API (what Railway runs in production)
uvicorn src.api.main:app --reload --port 8005

# Optional one-time setup for Gemini File Search RAG stores
python scripts/setup_file_stores.py

# CLI: classify a local document
python -m src.main classify --file path/to/document.pdf

# CLI: start chat interface
python -m src.main chat
```

## Feed Ingestion

Pull fresh evidence candidates from the cybersecurity feeds configured in
`src/ingestion/feeds.json` (Krebs, Schneier, The Hacker News, Dark Reading,
Google Security Blog):

```bash
# Preview: fetch + normalize + dedupe, print what WOULD be ingested.
# Makes no Gemini calls and writes nothing.
python -m src.ingestion.run --dry-run

# Cap the number of new articles
python -m src.ingestion.run --dry-run --limit 5

# Real ingestion: classifies each new article with Gemini and stores it
# through the same pipeline as /api/submit (requires GEMINI_API_KEY + DB)
python -m src.ingestion.run --limit 10
```

## Tests

```bash
python -m pytest tests/ -q
```

The suite is fully offline (fixture RSS/Atom XML, stubbed DB) - no API keys needed.

## Classification Categories

| Category | Description |
|----------|-------------|
| **Replace** | AI will fully automate this task (>70% AI) |
| **Augment** | AI assists but humans essential (40-70% AI) |
| **Remain Human** | Must stay human (ethics, legal, accountability) |
| **New Task** | AI enables new capabilities not in DCWF |

## Project Structure

```
ai-horizon-python/
├── src/
│   ├── api/            # FastAPI app (main.py) + PostgreSQL client (db.py)
│   ├── extraction/     # Content extractors (PDF, DOCX, YouTube, web)
│   ├── classification/ # AI classification logic
│   ├── ingestion/      # RSS/Atom feed ingestion (feeds.json + dry-run CLI)
│   ├── storage/        # Gemini File Search integration
│   ├── agents/         # Conversational RAG agent
│   └── utils/          # Helper functions
├── data/
│   └── dcwf/           # DCWF reference data
├── scripts/            # Setup and utility scripts
└── tests/              # Offline pytest suite (fixtures in tests/fixtures/)
```

## License

Research use only - CSUSB AI Horizon Project
