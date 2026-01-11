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
Next.js 16        FastAPI           Supabase
Tailwind CSS v4   Gemini AI         PostgreSQL
shadcn/ui         Python 3.11
React Query       RAG Pipeline
```

## Getting Started

### Prerequisites
- Node.js 18+
- Python 3.11+
- Supabase account (free tier works)
- Google Gemini API key

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
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Add your environment variables
uvicorn src.api.main:app --reload --port 8005
```

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
