# AI Horizon deployment and development

## Current layout

| Component | Source | Runtime |
| --- | --- | --- |
| Backend and legacy static UI | `ai-horizon-python/ai-horizon-python/` in this repository | FastAPI/Uvicorn on Railway |
| Evidence persistence | `src/api/db.py` | Railway PostgreSQL; JSON evidence fallback when no database is available |
| Managed retrieval | Gemini File Search | DCWF, evidence, and resource stores |
| Next.js frontend | Separate private `Bighabz/ai-horizon-frontend` repository | Vercel |

The backend deployment tracks `master`. Its Railway root directory is `ai-horizon-python/ai-horizon-python`; `railway.toml` starts Uvicorn with Railway's `PORT` and checks `/api/stats`.

The broader research initiative is at [theaihorizon.org](https://theaihorizon.org/). Configure the frontend with your own backend URL through `NEXT_PUBLIC_API_URL`. Deployment hostnames are kept in private configuration.

## Local backend

```bash
git clone https://github.com/Bighabz/AI-Horizon.git
cd AI-Horizon/ai-horizon-python/ai-horizon-python
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
uvicorn src.api.main:app --reload --port 8005
```

Configure `.env` before starting. Supply `GEMINI_API_KEY` for AI operations; leave `DATABASE_URL` empty to use the local JSON fallback. Set valid File Search store names to enable the corresponding retrieval features. The API is at `http://localhost:8005`, with a legacy static interface at `/` and API documentation at `/docs`.

To create File Search stores, run `python scripts/setup_file_stores.py` and save the resulting store names in your environment. See [.env.example](ai-horizon-python/ai-horizon-python/.env.example) for the authoritative variable list.

## Environment configuration

| Variables | Purpose |
| --- | --- |
| `GEMINI_API_KEY`, optional `_2`/`_3` keys | Model access and configured fallback keys |
| `DATABASE_URL` | Production PostgreSQL connection; omit locally for the JSON fallback |
| `RAILWAY_DATABASE_URL` | Public database connection for local maintenance scripts |
| `DCWF_STORE_NAME`, `EVIDENCE_STORE_NAME`, `RESOURCES_STORE_NAME` | Gemini File Search stores |
| `ADMIN_API_KEY` | Authentication for protected administration endpoints |
| `YOUTUBE_API_KEY` | Optional YouTube metadata support |
| `WEBSHARE_PROXY_USERNAME` / `WEBSHARE_PROXY_PASSWORD`, or `YT_PROXY_URL` | Optional transcript proxy |
| `YT_GEMINI_FALLBACK` | Gemini transcription fallback, enabled by default when configured |
| `LOG_LEVEL` | Logging verbosity |

Set production backend secrets in Railway's service variables. Keep `.env` files and database credentials out of Git. Dumpling AI is no longer used by the current extraction pipeline.

## API routes

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/api/health` | API status and configuration summary |
| GET | `/api/stats` | Knowledge-base statistics and Railway health check |
| POST | `/api/chat` | RAG assistant |
| GET / POST | `/api/search` | Search evidence and task mappings |
| POST | `/api/submit` | Submit a URL for classification |
| POST | `/api/upload` | Upload evidence |
| GET | `/api/evidence/artifact/{artifact_id}` | Retrieve an evidence artifact |
| GET | `/api/evidence/{task_id}` | Retrieve evidence for a task |
| GET | `/api/roles` | Work-role reference data |
| GET | `/api/resources` | Learning resources |
| GET | `/api/skills` | Skills matrix |
| GET | `/api/file-stores/stats` | Protected File Search administration |

Use `/docs` for request and response schemas. `/` serves the legacy UI; it is not the health endpoint.

## Separate frontend

With access to the private frontend repository:

```bash
git clone https://github.com/Bighabz/ai-horizon-frontend.git
cd ai-horizon-frontend
npm install
cp .env.example .env.local
npm run dev
```

Use Node.js 20.9 or later. Set `NEXT_PUBLIC_API_URL=http://localhost:8005` for local backend development. Consult the frontend's own `.env.example` for its remaining public configuration.


## Verification

From the backend directory, run `python -m pytest tests/ -q` for the offline fixture-based suite. With the API running, check `/api/health`, `/api/stats`, and `/docs`. AI chat and classification require valid model credentials and their configured stores.

For ingestion, `python -m src.ingestion.run --dry-run --limit 5` previews normalized feed candidates without classifying or storing them. It still fetches the configured public feeds.
