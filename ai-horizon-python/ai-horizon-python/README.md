# AI Horizon - Python RAG Pipeline

An AI-powered classification system for analyzing how artificial intelligence impacts the cybersecurity workforce, built on the DCWF (Department of Defense Cyber Workforce Framework).

## Project Background

This is an NSF-funded research project at California State University San Bernardino, led by Dr. Vincent Nestler. The goal is to collect and classify "social proof" artifacts that demonstrate AI's impact on cybersecurity jobs.

## Features

- **Multi-format extraction**: PDF, DOCX, YouTube, web articles
- **AI Classification**: Categorize artifacts as Replace, Augment, Remain Human, or New Task
- **DCWF Mapping**: Link artifacts to specific cybersecurity workforce tasks
- **RAG-powered queries**: Ask questions about your classified artifacts
- **Export capabilities**: Generate reports in CSV/JSON format

## Tech Stack

- **Python 3.11+**
- **Google Gemini API** (2.5 Flash/Pro)
- **Gemini File Search** (Managed RAG)
- **Typer** (CLI framework)
- **Pydantic** (Data validation)

## Quick Start

```bash
# Clone and setup
git clone <repo>
cd ai-horizon-python
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Add your GEMINI_API_KEY to .env

# Initialize
python scripts/setup_file_stores.py
python scripts/import_dcwf.py

# Classify an artifact
python -m src.main classify --file path/to/document.pdf

# Start chat interface
python -m src.main chat
```

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
│   ├── extraction/     # Content extractors (PDF, DOCX, YouTube, web)
│   ├── classification/ # AI classification logic
│   ├── storage/        # Gemini File Search integration
│   ├── agents/         # Conversational RAG agent
│   └── utils/          # Helper functions
├── data/
│   └── dcwf/           # DCWF reference data
├── scripts/            # Setup and utility scripts
└── tests/              # Test suite
```

## License

Research use only - CSUSB AI Horizon Project
