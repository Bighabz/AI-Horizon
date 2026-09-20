# AI Horizon backend

This service turns research into a searchable collection of evidence about AI and cybersecurity work. The [project overview](../../README.md) explains the features and local installation. This guide covers the parts you configure after the server starts.

## What happens to a submission

1. The service reads a supported document, web article, or YouTube video.
2. Gemini proposes an AI-impact classification and related cybersecurity tasks.
3. The service checks for duplicate content and saves the result.
4. The website can retrieve that evidence for search, role exploration, and chat.

YouTube extraction first tries available captions, then an optional configured proxy, then Gemini transcription if enabled. A generated transcript can contain mistakes, so check it against the source when accuracy matters.

## Configure your research collection

`GEMINI_API_KEY` enables model calls. The File Search settings identify the collections used to retrieve supporting material:

| Setting | Collection |
| --- | --- |
| `DCWF_STORE_NAME` | Cybersecurity task and role reference material |
| `EVIDENCE_STORE_NAME` | Research about AI's impact on tasks |
| `RESOURCES_STORE_NAME` | Training and learning resources |

`python scripts/setup_file_stores.py` creates the DCWF and evidence stores. It prints the evidence name as `ARTIFACTS_STORE_NAME`, an older name the backend still accepts; you can save that value as `EVIDENCE_STORE_NAME`. The helper creates empty stores. It does not load the full reference collection or create a resources store.

The repository includes `DCWFMASTER.xlsx` and `resources.csv` at its root as reference material. Full research chat needs a configured and populated collection. The setup script's historical `import_dcwf.py` suggestion refers to a file that is not included; do not run that command.

For basic local evidence storage, leave `DATABASE_URL` empty. Configure PostgreSQL for the feed ingestion workflow and a durable shared deployment. Set a new `ADMIN_API_KEY` before using protected administration endpoints.

## Classify a document from the terminal

From this backend directory, with the environment activated:

```bash
python -m src.main classify --file path/to/document.pdf
python -m src.main chat
```

These commands use your model account and the collection settings in `.env`. For web requests and uploads, open the running service's `/docs` page to see the expected fields and try an endpoint.

## Collect articles from feeds

Choose sources in `src/ingestion/feeds.json`, then preview a small batch:

```bash
python -m src.ingestion.run --dry-run --limit 5
```

The preview fetches the configured public feeds and shows the candidates. It does not classify or save them. After reviewing the results, a real run uses Gemini and the configured database:

```bash
python -m src.ingestion.run --limit 10
```

## Main API routes

| Route | Purpose |
| --- | --- |
| `GET /api/health` | Check service status. |
| `GET /api/stats` | Read collection counts. |
| `POST /api/submit` | Submit a research URL. |
| `POST /api/upload` | Upload a supported document. |
| `GET` or `POST /api/search` | Search evidence and task mappings. |
| `POST /api/chat` | Ask the assistant. |
| `GET /api/roles`, `/api/skills`, `/api/resources` | Explore roles, skills, and learning material. |

See [DEPLOYMENT.md](../../DEPLOYMENT.md) and the live `/docs` page for the full route and configuration reference.

## Find the implementation

| Directory | Responsibility |
| --- | --- |
| `src/api/` | Web requests and database storage |
| `src/extraction/` | Reading articles, documents, and videos |
| `src/classification/` | Research classification |
| `src/ingestion/` | Feed discovery and processing |
| `src/storage/` | Gemini File Search collections |
| `src/agents/` | Conversational assistant |
| `tests/` | Offline checks using sample data and mocked services |

Run `python -m pytest tests/ -q` before changing the service. Review source evidence and model output together; passing tests does not establish that every research classification is correct.
