# AI Horizon

AI Horizon helps answer a practical question: **how is AI changing the work people do in cybersecurity?**

It brings research papers, articles, videos, and learning resources into one place, then connects them to cybersecurity job tasks. Researchers can review the evidence, students can explore roles, and an AI assistant can help explain what the findings mean.

The project is part of NSF-funded research at California State University, San Bernardino, led by Dr. Vincent Nestler. I worked on the research project and built its document-processing and AI workflows.

[Visit the research website](https://theaihorizon.org/) · [Run the backend](#run-it-locally) · [Developer guide](ai-horizon-python/ai-horizon-python/README.md)

## What it does

| Feature | What someone can use it for |
| --- | --- |
| **Explore cybersecurity roles** | Browse tasks and skills associated with different work roles and see how the collected evidence relates to them. |
| **Search the evidence** | Find relevant papers, articles, and other source material instead of relying on an AI answer alone. |
| **Ask the assistant** | Discuss roles, skills, and career questions using the configured research collection. The assistant also supports quiz and learning-plan conversations. |
| **Add research** | Submit a web page or YouTube link, or upload a PDF or Word document, for text extraction and classification. |
| **Connect findings to job tasks** | Map evidence to the Department of Defense Cyber Workforce Framework, or DCWF: 1,350 tasks across 52 work roles. |
| **Organize learning resources** | Associate training material with relevant tasks and roles. |
| **Keep collecting evidence** | Read configured news and research feeds, check for duplicates, and bring new articles into the same process. |

For example, a researcher could submit an article about an AI tool that reviews security alerts, see which tasks it relates to, and inspect why the model classified it as helping an analyst.

## How the classifications work

| Label | Meaning |
| --- | --- |
| **Replace** | The evidence suggests AI could perform the task. |
| **Augment** | AI helps a person do the task. |
| **Remain Human** | Human judgment, responsibility, or interaction remains central. |
| **New Task** | AI introduces work that was not previously part of the role. |

These labels organize research for review. They are not predictions that an entire job will disappear, and AI-generated mappings still need a person to check them.

## What's in this repository

This is the **Python backend**, including the research-processing code, reference data, tests, and an earlier browser interface. It uses FastAPI, Google Gemini, and PostgreSQL, with a local JSON file available for basic evidence storage.

The newer Next.js website is maintained in a separate private repository. You can run this backend and its included interface without access to that website. Search and chat over the full research collection need your own configured Gemini File Search stores.

## Run it locally

You need **Git, Python 3.11 or later**, and a Gemini API key for AI features.

```bash
git clone https://github.com/Bighabz/AI-Horizon.git
cd AI-Horizon/ai-horizon-python/ai-horizon-python
python -m venv .venv
```

Activate the environment with `source .venv/bin/activate` on macOS/Linux or `.\.venv\Scripts\Activate.ps1` in Windows PowerShell. Then:

```bash
python -m pip install -r requirements.txt
python -c "from pathlib import Path; import shutil; p=Path('.env'); shutil.copyfile('.env.example',p) if not p.exists() else None"
```

Open `.env` and fill in `GEMINI_API_KEY`. For a local first run, leave `DATABASE_URL` empty to use the JSON evidence store. Remove example File Search store names until you have created your own stores; placeholder names do not connect to the research collection.

Start the app:

```bash
python -m uvicorn src.api.main:app --reload --port 8005
```

Open **http://localhost:8005** for the included interface, **http://localhost:8005/docs** for interactive API documentation, or **http://localhost:8005/api/health** to check that the server is running.

For a first AI request, submit a public article you can read yourself, then compare its classification with the source. Missing credentials or research stores will limit which features work. AI requests use your provider account and may incur charges.

## Next steps

- The [backend guide](ai-horizon-python/ai-horizon-python/README.md) covers research stores, document classification, and feed collection.
- The [deployment guide](DEPLOYMENT.md) lists environment settings and API routes. The backend is configured for Railway.
- [The research website](https://theaihorizon.org/) explains the broader initiative.

From the backend directory, run the offline tests with:

```bash
python -m pytest tests/ -q
```

Keep API keys, database credentials, and machine-specific settings in local environment files or your deployment's secret settings. They do not belong in this repository.
