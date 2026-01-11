# AI Horizon Project - Claude Code Context

## Project Overview

**AI Horizon** is an NSF-funded research initiative at California State University San Bernardino led by **Dr. Vincent Nestler**. The project analyzes how AI is impacting the cybersecurity workforce by classifying "social proof" artifacts against the **DCWF (Department of Defense Cyber Workforce Framework)**.

## Migration Context

We are migrating from:
- **n8n** (low-code automation) → **Pure Python**
- **Supabase** (PostgreSQL + pgvector) → **Gemini File Search** (managed RAG)
- **OpenAI embeddings** → **Gemini embeddings** (built-in)

## Core Objective

Build a Python-based AI classification pipeline that:
1. Ingests artifacts (documents, YouTube videos, web articles, PDFs)
2. Extracts/transcribes content
3. Classifies each artifact against DCWF tasks
4. Stores everything in Gemini File Search for RAG queries
5. Provides a conversational interface for querying the knowledge base

---

## Classification Framework

### Four Impact Categories

| Category | Description | AI Cognitive Load |
|----------|-------------|-------------------|
| **Replace** | AI will fully automate this task | >70% |
| **Augment** | AI assists but humans essential for oversight | 40-70% |
| **Remain Human** | Task must stay human (ethics, legal, accountability) | <40% |
| **New Task** | AI enables entirely new capabilities not in DCWF | N/A |

### Classification Criteria

Each artifact should be scored on:
- **Credibility** (0.0-1.0): Source reliability
- **Impact** (0.0-1.0): Workforce transformation significance
- **Specificity** (0.0-1.0): How precisely it maps to DCWF tasks
- **Confidence** (0.0-1.0): Overall classification confidence

---

## DCWF Framework Reference

The DCWF (Defense Cyber Workforce Framework) contains ~1,350 tasks organized by:
- **Task ID**: e.g., "T0001", "T0597"
- **NIST SP ID**: Reference to NIST standards
- **Task Description**: What the task involves
- **Work Role**: e.g., "Threat Analyst", "Security Architect"
- **Work Role ID**: e.g., "AN-TWA-001"
- **Competency Area**: Skill category

### Sample DCWF Tasks (for context)

```
T0597 - Analyze threat intelligence data and correlate with internal security events
T0004 - Develop and implement security policies and procedures
T0166 - Perform penetration testing and vulnerability assessments
T0432 - Collect and analyze network traffic data
```

---

## Data Models

### Artifact (Document/Evidence)

```python
@dataclass
class Artifact:
    artifact_id: str
    title: str
    content: str
    source_url: str
    source_type: str  # pdf, docx, youtube, web, tiktok
    
    # Classification
    classification: str  # Replace, Augment, Remain Human, New Task
    confidence: float
    rationale: str
    
    # Scores
    credibility: float
    impact: float
    specificity: float
    
    # DCWF Mapping
    dcwf_task_ids: List[str]
    work_roles: List[str]
    
    # Metadata
    retrieved_on: datetime
    user_id: Optional[str]
```

### Classification Result

```python
@dataclass
class ClassificationResult:
    classification: str
    confidence: float
    rationale: str
    scores: dict  # credibility, impact, specificity
    dcwf_tasks: List[dict]  # task_id, relevance_score, impact_description
    work_roles: List[str]
    key_findings: List[str]
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  INPUT SOURCES                                              │
│  • CLI upload (PDF, DOCX, TXT)                              │
│  • YouTube URL → Transcription                              │
│  • Web URL → Scraping                                       │
│  • Batch processing from CSV/directory                      │
└─────────────────────┬───────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  EXTRACTION LAYER (Python)                                  │
│  • PyPDF2 / pdfplumber for PDFs                             │
│  • python-docx for DOCX                                     │
│  • youtube-transcript-api for YouTube                       │
│  • BeautifulSoup/trafilatura for web                        │
└─────────────────────┬───────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  AI CLASSIFICATION (Gemini)                                 │
│  • Gemini 2.5 Flash/Pro for classification                  │
│  • Structured output with Pydantic                          │
│  • DCWF context from File Search                            │
└─────────────────────┬───────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  STORAGE (Gemini File Search)                               │
│  • FileSearchStore for DCWF reference docs                  │
│  • FileSearchStore for classified artifacts                 │
│  • Built-in citations and retrieval                         │
└─────────────────────┬───────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  QUERY INTERFACE                                            │
│  • CLI chat interface                                       │
│  • "What tasks are classified as Replace?"                  │
│  • "Show me artifacts about threat intelligence"            │
│  • Export to CSV/JSON for reporting                         │
└─────────────────────────────────────────────────────────────┘
```

---

## Gemini File Search Implementation

### Setup File Search Stores

We need two stores:
1. **dcwf_reference** - Contains DCWF task definitions for context
2. **horizon_artifacts** - Contains classified artifacts for RAG queries

```python
from google import genai
from google.genai import types

client = genai.Client()

# Create stores
dcwf_store = client.file_search_stores.create(
    config={'display_name': 'dcwf-reference'}
)

artifacts_store = client.file_search_stores.create(
    config={'display_name': 'horizon-artifacts'}
)
```

### Upload and Index Documents

```python
# Upload DCWF reference
operation = client.file_search_stores.upload_to_file_search_store(
    file='dcwf_tasks.json',
    file_search_store_name=dcwf_store.name,
    config={'display_name': 'DCWF Master Task List'}
)

# Wait for indexing
while not operation.done:
    time.sleep(5)
    operation = client.operations.get(operation)
```

### Query with RAG

```python
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Which DCWF tasks relate to threat intelligence analysis?",
    config=types.GenerateContentConfig(
        tools=[
            types.Tool(
                file_search=types.FileSearch(
                    file_search_store_names=[dcwf_store.name]
                )
            )
        ]
    )
)
```

---

## Classification Prompt Template

```python
CLASSIFICATION_SYSTEM_PROMPT = """
You are an AI impact assessment expert for the AI Horizon Project, specializing in 
cybersecurity workforce transformation analysis.

Your task is to analyze artifacts (documents, videos, articles) and classify them 
according to the DCWF (Defense Cyber Workforce Framework).

## Classification Categories

1. **Replace**: AI will fully automate this task
   - >70% of cognitive load handled by AI
   - Routine, repetitive tasks with clear patterns
   - Examples: Log parsing, signature-based detection, report generation

2. **Augment**: AI significantly enhances human capability
   - 40-70% AI cognitive load, humans essential for oversight
   - Complex tasks requiring both automation and human expertise
   - Examples: Threat intelligence correlation, incident triage, code review

3. **Remain Human**: Task must remain primarily human-performed
   - High-stakes decisions, legal/ethical requirements
   - Requires human accountability and judgment
   - Examples: Policy development, crisis leadership, breach notification

4. **New Task**: AI enables entirely new capabilities
   - Capabilities that didn't exist before AI
   - Novel approaches to security problems
   - Examples: Behavioral anomaly detection, AI-powered red teaming

## Output Format (JSON)

{
    "classification": "Replace|Augment|Remain Human|New Task",
    "confidence": 0.0-1.0,
    "rationale": "Brief explanation based on content",
    "scores": {
        "credibility": 0.0-1.0,
        "impact": 0.0-1.0,
        "specificity": 0.0-1.0
    },
    "dcwf_tasks": [
        {
            "task_id": "T0XXX",
            "relevance_score": 0.0-1.0,
            "impact_description": "How this artifact relates to the task"
        }
    ],
    "work_roles": ["Role 1", "Role 2"],
    "key_findings": ["Finding 1", "Finding 2"]
}
"""
```

---

## File Structure

```
ai-horizon-python/
├── README.md
├── pyproject.toml
├── requirements.txt
├── .env.example
├── .gitignore
│
├── src/
│   ├── __init__.py
│   ├── main.py                 # CLI entry point
│   ├── config.py               # Configuration management
│   │
│   ├── extraction/
│   │   ├── __init__.py
│   │   ├── base.py             # Base extractor class
│   │   ├── pdf.py              # PDF extraction
│   │   ├── docx.py             # DOCX extraction
│   │   ├── youtube.py          # YouTube transcription
│   │   ├── web.py              # Web scraping
│   │   └── router.py           # Route by content type
│   │
│   ├── classification/
│   │   ├── __init__.py
│   │   ├── classifier.py       # Main classification logic
│   │   ├── prompts.py          # System prompts
│   │   └── models.py           # Pydantic models
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── file_search.py      # Gemini File Search wrapper
│   │   └── export.py           # CSV/JSON export
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── chat_agent.py       # Conversational RAG agent
│   │   └── tools.py            # Agent tools
│   │
│   └── utils/
│       ├── __init__.py
│       └── helpers.py
│
├── data/
│   ├── dcwf/
│   │   └── dcwf_tasks.json     # DCWF master task list
│   └── samples/                # Sample artifacts for testing
│
├── tests/
│   ├── __init__.py
│   ├── test_extraction.py
│   ├── test_classification.py
│   └── test_storage.py
│
└── scripts/
    ├── setup_file_stores.py    # Initialize Gemini File Search stores
    ├── import_dcwf.py          # Import DCWF data
    └── batch_classify.py       # Batch processing script
```

---

## Environment Variables

```env
# .env
GEMINI_API_KEY=your_gemini_api_key
DCWF_STORE_NAME=fileSearchStores/dcwf-reference-xxxxx
ARTIFACTS_STORE_NAME=fileSearchStores/horizon-artifacts-xxxxx

# Optional: For YouTube API (if youtube-transcript-api needs auth)
YOUTUBE_API_KEY=optional_youtube_key
```

---

## Dependencies

```txt
# requirements.txt
google-genai>=0.8.0
pydantic>=2.0.0
python-dotenv>=1.0.0
typer>=0.9.0
rich>=13.0.0

# Extraction
pypdf2>=3.0.0
pdfplumber>=0.10.0
python-docx>=1.0.0
youtube-transcript-api>=0.6.0
trafilatura>=1.6.0
beautifulsoup4>=4.12.0
requests>=2.31.0

# Testing
pytest>=8.0.0
pytest-asyncio>=0.23.0
```

---

## Getting Started (for Claude Code)

1. **Set up the environment**
   ```bash
   cd ai-horizon-python
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure API keys**
   ```bash
   cp .env.example .env
   # Add your GEMINI_API_KEY
   ```

3. **Initialize File Search stores**
   ```bash
   python scripts/setup_file_stores.py
   ```

4. **Import DCWF data**
   ```bash
   python scripts/import_dcwf.py --file data/dcwf/dcwf_tasks.json
   ```

5. **Run classification**
   ```bash
   python -m src.main classify --file path/to/artifact.pdf
   ```

6. **Start chat interface**
   ```bash
   python -m src.main chat
   ```

---

## Key Implementation Notes

1. **Gemini File Search is the RAG backbone** - No need for Supabase/pgvector
2. **Use structured outputs** - Gemini 2.5 supports JSON schema enforcement
3. **Two File Search stores** - One for DCWF reference, one for artifacts
4. **Built-in citations** - File Search returns which documents were used
5. **Async where possible** - Use async/await for I/O operations

---

## Next Steps for Claude Code

1. Create the basic project structure
2. Implement extraction modules (start with PDF/DOCX)
3. Set up Gemini File Search stores
4. Build the classification pipeline
5. Create the chat agent
6. Add batch processing
7. Implement export functionality

---

## Reference Links

- [Gemini File Search Documentation](https://ai.google.dev/gemini-api/docs/file-search)
- [Google GenAI Python SDK](https://github.com/google/generative-ai-python)
- [DCWF Framework](https://niccs.cisa.gov/workforce-development/nice-framework)
