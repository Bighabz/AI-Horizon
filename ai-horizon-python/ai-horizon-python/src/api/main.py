"""
AI Horizon Web API
FastAPI backend for the AI Horizon research portal.

Features:
- RAG-powered chat using Gemini File Search
- Search/filter by job role, DCWF task, AI tool
- Submit new artifacts with classification
- Deduplication before storage
- Session-based conversation memory
"""

import hashlib
import json
import logging
import os
import re
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from dotenv import load_dotenv

# Load .env from project root BEFORE any other imports that might use env vars
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path, override=True)

from fastapi import FastAPI, HTTPException, BackgroundTasks, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import tempfile
from pydantic import BaseModel, Field, HttpUrl
from google import genai
from google.genai import types

# Supabase client for database storage
from .supabase_client import load_artifacts, save_artifact, search_artifacts, get_stats as get_supabase_stats, check_url_duplicate, get_all_source_urls

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Custom exception for rate limits (allows graceful handling)
class RateLimitError(Exception):
    """Raised when API rate limit is exhausted after all retries."""
    pass

# Configuration - read AFTER dotenv is loaded
DCWF_STORE_NAME = os.getenv("DCWF_STORE_NAME")
ARTIFACTS_STORE_NAME = os.getenv("ARTIFACTS_STORE_NAME")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# API Key rotation support - load multiple keys
API_KEYS = []
primary_key = os.getenv("GEMINI_API_KEY")
if primary_key:
    API_KEYS.append(primary_key)
# Support GEMINI_API_KEY_2, GEMINI_API_KEY_3, etc.
for i in range(2, 10):
    key = os.getenv(f"GEMINI_API_KEY_{i}")
    if key:
        API_KEYS.append(key)

logger.info(f"Config loaded: {len(API_KEYS)} API key(s), DCWF={DCWF_STORE_NAME}, ARTIFACTS={ARTIFACTS_STORE_NAME}")

# API key rotation state
current_key_index = 0


def get_client():
    """Get a Gemini client with the current API key."""
    global current_key_index
    if not API_KEYS:
        return None
    return genai.Client(api_key=API_KEYS[current_key_index])


def rotate_api_key():
    """Rotate to the next API key after rate limit."""
    global current_key_index
    if len(API_KEYS) > 1:
        old_index = current_key_index
        current_key_index = (current_key_index + 1) % len(API_KEYS)
        logger.warning(f"Rotated API key: {old_index} -> {current_key_index}")
        return True
    return False


def call_with_retry(func, max_retries=3):
    """Call a Gemini API function with retry and key rotation on rate limit."""
    import time
    import re
    last_error = None

    for attempt in range(max_retries):
        try:
            return func(get_client())
        except Exception as e:
            last_error = e
            error_str = str(e).lower()

            # Check for rate limit or overloaded errors
            if "503" in error_str or "overloaded" in error_str or "429" in error_str or "rate" in error_str or "quota" in error_str:
                logger.warning(f"API error (attempt {attempt + 1}): {e}")

                # Try rotating to another key
                if rotate_api_key():
                    continue

                # Extract retry delay from error message if available
                retry_match = re.search(r'retry in (\d+)', str(e).lower())
                if retry_match and attempt == max_retries - 1:
                    # On last attempt, wait the full suggested time
                    wait_time = min(int(retry_match.group(1)), 60)
                else:
                    wait_time = 2 ** attempt  # Exponential backoff: 1, 2, 4 seconds

                logger.info(f"Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            elif "400" in error_str or "invalid_argument" in error_str:
                # Bad request - don't retry, let caller handle gracefully
                logger.warning(f"Bad request error: {e}")
                raise e  # Immediately raise so caller's exception handler can catch it
            else:
                # Non-retryable error
                raise e

    # If we exhausted retries on a rate limit error, raise our custom exception
    error_str = str(last_error).lower() if last_error else ""
    if "429" in error_str or "quota" in error_str or "rate" in error_str:
        raise RateLimitError(f"API rate limit exhausted after {max_retries} retries. Please wait a minute.")
    raise last_error


# Initialize primary client for startup check
client = get_client()

# Semantic correlations for search expansion
TERM_CORRELATIONS = {
    # Security Operations
    "threat analysis": ["threat hunting", "threat intelligence", "IOC analysis", "adversary tracking"],
    "vulnerability": ["CVE", "exploit", "weakness", "security flaw", "patch management"],
    "incident response": ["IR", "breach response", "security incident", "forensics"],
    "penetration testing": ["pentesting", "ethical hacking", "red team", "offensive security"],

    # AI/ML Terms
    "machine learning": ["ML", "AI", "neural network", "deep learning", "predictive analytics"],
    "automation": ["SOAR", "orchestration", "playbook", "automated response"],
    "chatgpt": ["GPT", "LLM", "large language model", "generative AI", "AI assistant"],

    # Roles
    "analyst": ["SOC analyst", "security analyst", "threat analyst", "intelligence analyst"],
    "engineer": ["security engineer", "DevSecOps", "infrastructure", "platform engineer"],
    "architect": ["security architect", "solutions architect", "enterprise architect"],

    # Tasks
    "monitoring": ["alerting", "detection", "SIEM", "log analysis", "observability"],
    "compliance": ["audit", "GRC", "regulatory", "policy", "standards"],
    "risk assessment": ["risk analysis", "threat modeling", "security assessment"],
}


def expand_search_terms(query: str) -> str:
    """Expand search query with semantic correlations."""
    query_lower = query.lower()
    expanded_terms = set()

    for term, synonyms in TERM_CORRELATIONS.items():
        if term in query_lower:
            expanded_terms.update(synonyms[:2])  # Add top 2 synonyms
        for synonym in synonyms:
            if synonym.lower() in query_lower:
                expanded_terms.add(term)
                break

    if expanded_terms:
        return f"{query} (related: {', '.join(list(expanded_terms)[:5])})"
    return query

# Initialize FastAPI
app = FastAPI(
    title="AI Horizon API",
    description="Research portal for AI's impact on cybersecurity workforce",
    version="1.0.0",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session storage (use Redis in production)
sessions: dict[str, list[dict]] = {}
artifact_hashes: set[str] = set()  # For deduplication

# ============================================================================
# Local Evidence Store (JSON-based RAG)
# ============================================================================

EVIDENCE_STORE_PATH = Path(__file__).parent.parent.parent / "evidence_store.json"
evidence_store: list[dict] = []  # In-memory cache of evidence


def load_evidence_store():
    """Load evidence store from Supabase (primary) or JSON file (fallback)."""
    global evidence_store
    try:
        # Try Supabase first
        evidence_store = load_artifacts()
        if evidence_store:
            logger.info(f"Loaded {len(evidence_store)} artifacts from Supabase")
            return
    except Exception as e:
        logger.warning(f"Supabase not available, falling back to JSON: {e}")

    # Fallback to JSON file
    if EVIDENCE_STORE_PATH.exists():
        try:
            with open(EVIDENCE_STORE_PATH, 'r', encoding='utf-8') as f:
                evidence_store = json.load(f)
            logger.info(f"Loaded {len(evidence_store)} artifacts from JSON file")
        except Exception as e:
            logger.error(f"Failed to load evidence store: {e}")
            evidence_store = []
    else:
        evidence_store = []
        logger.info("No existing evidence store found, starting fresh")


def save_evidence_store():
    """Save evidence store to JSON file."""
    try:
        resolved_path = EVIDENCE_STORE_PATH.resolve()
        logger.info(f"Saving evidence store to: {resolved_path}")

        # Ensure parent directory exists
        resolved_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to temp file first, then rename (atomic write)
        temp_path = resolved_path.with_suffix('.json.tmp')
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(evidence_store, f, indent=2, default=str)
            f.flush()
            import os
            os.fsync(f.fileno())  # Force write to disk

        # Rename temp file to actual file (atomic on most systems)
        temp_path.replace(resolved_path)

        logger.info(f"Saved {len(evidence_store)} artifacts to evidence store at {resolved_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save evidence store to {EVIDENCE_STORE_PATH}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def add_to_evidence_store(artifact_data: dict) -> bool:
    """Add artifact to Supabase (primary) and local cache."""
    global evidence_store
    try:
        logger.info(f"Adding artifact to evidence store: {artifact_data.get('artifact_id')}")

        # Save to Supabase
        supabase_success = save_artifact(artifact_data)
        if supabase_success:
            logger.info("Successfully saved artifact to Supabase")

        # Also add to in-memory cache
        evidence_store.append(artifact_data)

        # Backup to JSON file
        save_evidence_store()

        return supabase_success or True
    except Exception as e:
        logger.error(f"Error adding to evidence store: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def search_evidence_store(query: str, limit: int = 5) -> list[dict]:
    """
    Search local evidence store for relevant artifacts.

    Looks for matches in:
    - DCWF task IDs (e.g., AN-T1019)
    - Keywords in title, content, rationale
    - Work roles
    - Classification types
    """
    if not evidence_store:
        return []

    query_lower = query.lower()
    results = []

    # Extract DCWF task IDs from query (pattern like XX-Txxxx or XX-XXX)
    dcwf_pattern = re.compile(r'\b([A-Z]{2}-[A-Z]?\d{3,5}|[A-Z]{2}-[A-Z]{2,3})\b', re.IGNORECASE)
    dcwf_ids = dcwf_pattern.findall(query.upper())

    for artifact in evidence_store:
        score = 0

        # Check DCWF task IDs
        artifact_tasks = artifact.get("dcwf_tasks", [])
        for task in artifact_tasks:
            task_id = task.get("task_id", "") if isinstance(task, dict) else str(task)
            if any(dcwf_id in task_id.upper() for dcwf_id in dcwf_ids):
                score += 10  # High priority for exact task ID match

        # Check title
        title = artifact.get("title", "").lower()
        if query_lower in title:
            score += 5

        # Check content (first 2000 chars)
        content = (artifact.get("content") or "")[:2000].lower()
        if query_lower in content:
            score += 3

        # Check rationale
        rationale = artifact.get("rationale", "").lower()
        if query_lower in rationale:
            score += 2

        # Check work roles
        work_roles = artifact.get("work_roles", [])
        for role in work_roles:
            if query_lower in role.lower():
                score += 3

        # Check key findings
        findings = artifact.get("key_findings", [])
        for finding in findings:
            if query_lower in finding.lower():
                score += 2

        # Check classification
        classification = artifact.get("classification", "").lower()
        if query_lower in classification:
            score += 2

        # Keyword matching for common terms
        keywords = ["task", "evidence", "ai", "automation", "replace", "augment", "threat", "security"]
        for keyword in keywords:
            if keyword in query_lower and keyword in content:
                score += 1

        if score > 0:
            results.append((score, artifact))

    # Sort by score descending and return top results
    results.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in results[:limit]]


def detect_evidence_query(message: str) -> bool:
    """
    Detect if user message is asking about evidence, tasks, or specific DCWF IDs.
    """
    message_lower = message.lower()

    # Keywords that suggest evidence/task query
    evidence_keywords = [
        "task", "evidence", "proof", "artifact", "source",
        "dcwf", "work role", "classification", "what tasks",
        "which tasks", "show me", "find", "search for"
    ]

    # Check for DCWF task ID pattern
    dcwf_pattern = re.compile(r'\b([A-Z]{2}-[A-Z]?\d{3,5}|[A-Z]{2}-[A-Z]{2,3})\b', re.IGNORECASE)
    if dcwf_pattern.search(message):
        return True

    # Check for evidence keywords
    return any(keyword in message_lower for keyword in evidence_keywords)


def build_context_from_evidence(relevant_evidence: list[dict]) -> str:
    """Build context string from relevant evidence for injection into prompt."""
    if not relevant_evidence:
        return ""

    context_parts = ["\n\n## Local Evidence Context\nThe following artifacts from our evidence store are relevant to this query:\n"]

    for i, artifact in enumerate(relevant_evidence, 1):
        context_parts.append(f"\n### Evidence {i}: {artifact.get('title', 'Untitled')}")
        context_parts.append(f"- **Classification**: {artifact.get('classification', 'Unknown')}")
        context_parts.append(f"- **Confidence**: {artifact.get('confidence', 0):.0%}")

        if artifact.get('rationale'):
            context_parts.append(f"- **Rationale**: {artifact.get('rationale')}")

        dcwf_tasks = artifact.get('dcwf_tasks', [])
        if dcwf_tasks:
            task_strs = []
            for task in dcwf_tasks[:3]:  # Limit to 3 tasks per artifact
                if isinstance(task, dict):
                    task_strs.append(f"{task.get('task_id', 'N/A')}: {task.get('task_name', 'N/A')}")
                else:
                    task_strs.append(str(task))
            context_parts.append(f"- **Related DCWF Tasks**: {', '.join(task_strs)}")

        work_roles = artifact.get('work_roles', [])
        if work_roles:
            context_parts.append(f"- **Work Roles**: {', '.join(work_roles[:3])}")

        findings = artifact.get('key_findings', [])
        if findings:
            context_parts.append(f"- **Key Findings**: {'; '.join(findings[:2])}")

        if artifact.get('source_url'):
            context_parts.append(f"- **Source**: {artifact.get('source_url')}")

    return "\n".join(context_parts)


# Load evidence store on startup
logger.info(f"Evidence store path resolved to: {EVIDENCE_STORE_PATH.resolve()}")
load_evidence_store()


# ============================================================================
# Data Models
# ============================================================================

class ClassificationType(str, Enum):
    REPLACE = "Replace"
    AUGMENT = "Augment"
    REMAIN_HUMAN = "Remain Human"
    NEW_TASK = "New Task"


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    output: str
    session_id: str
    sources: list[str] = []


class SearchRequest(BaseModel):
    query: Optional[str] = None
    job_role: Optional[str] = None
    dcwf_task: Optional[str] = None
    ai_tool: Optional[str] = None
    classification: Optional[ClassificationType] = None
    limit: int = Field(default=20, le=100)


class SearchResult(BaseModel):
    task_id: str
    task_name: str
    description: str
    classification: Optional[str] = None
    confidence: Optional[float] = None
    evidence_count: int = 0
    work_roles: list[str] = []


class ResourceType(str, Enum):
    """Type of learning resource."""
    VIDEO = "Video"
    COURSE = "Course"
    CERTIFICATION = "Certification"
    PLATFORM = "Platform"
    RESOURCE = "Resource"
    ARTICLE = "Article"
    TOOL = "Tool"
    BOOTCAMP = "Bootcamp"


class DifficultyLevel(str, Enum):
    """Difficulty level for resources."""
    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate"
    ADVANCED = "Advanced"
    EXPERT = "Expert"


class SubmitArtifactRequest(BaseModel):
    url: Optional[HttpUrl] = None
    content: Optional[str] = None
    title: Optional[str] = None
    source_type: str = "web"  # web, youtube, pdf, article
    resource_type: Optional[ResourceType] = None  # Video, Course, Certification, etc.
    difficulty: Optional[DifficultyLevel] = None  # Beginner, Intermediate, Advanced, Expert
    is_free: bool = True  # Free or premium content
    work_role: Optional[str] = None  # Associated DCWF work role
    session_id: Optional[str] = None


class SubmitArtifactResponse(BaseModel):
    success: bool
    artifact_id: Optional[str] = None
    is_duplicate: bool = False
    is_relevant: bool = True
    relevance_score: Optional[float] = None
    relevance_reason: Optional[str] = None
    stored: bool = True  # Whether the artifact was stored
    message: str
    classification: Optional[dict] = None


class EvidenceRequest(BaseModel):
    task_id: str


class EvidenceItem(BaseModel):
    artifact_id: str
    title: str
    source_url: Optional[str] = None
    source_type: str
    classification: str
    confidence: float
    rationale: str
    retrieved_on: str


# ============================================================================
# Helper Functions
# ============================================================================

def get_content_hash(content: str, url: Optional[str] = None) -> str:
    """Generate a hash for deduplication."""
    # Normalize content
    normalized = re.sub(r'\s+', ' ', content.lower().strip())[:5000]
    if url:
        # Include URL domain for uniqueness
        domain = urlparse(str(url)).netloc
        normalized = f"{domain}:{normalized}"
    return hashlib.sha256(normalized.encode()).hexdigest()[:32]


def normalize_url(url: str) -> str:
    """Normalize URL for comparison (remove tracking params, etc.)."""
    if not url:
        return ""
    url = url.strip().lower()
    # Remove common tracking parameters
    parsed = urlparse(url)
    # Remove fragment
    url = url.split('#')[0]
    # Remove trailing slash
    url = url.rstrip('/')
    # Remove www. prefix
    if parsed.netloc.startswith('www.'):
        url = url.replace('://www.', '://', 1)
    return url


def check_url_exists(url: str) -> Optional[dict]:
    """Check if a URL already exists in the evidence store or Supabase."""
    if not url:
        return None

    # First check Supabase (persistent storage)
    supabase_result = check_url_duplicate(url)
    if supabase_result:
        # Transform to expected format
        return {
            "artifact_id": f"artifact_{supabase_result['id'][:12]}" if supabase_result.get('id') else None,
            "title": supabase_result.get("file_name"),
            "source_url": supabase_result.get("source_url"),
            "classification": supabase_result.get("classification"),
            "confidence": supabase_result.get("confidence"),
            "rationale": supabase_result.get("rationale"),
            "stored_at": supabase_result.get("created_at"),
        }

    # Also check in-memory cache
    normalized = normalize_url(url)
    for artifact in evidence_store:
        stored_url = artifact.get("source_url")
        if stored_url and normalize_url(stored_url) == normalized:
            return artifact
    return None


def check_duplicate(content: str, url: Optional[str] = None) -> bool:
    """Check if content already exists (by hash or URL)."""
    # First check URL
    if url and check_url_exists(url):
        return True
    # Then check content hash
    content_hash = get_content_hash(content, url)
    return content_hash in artifact_hashes


def register_artifact(content: str, url: Optional[str] = None) -> str:
    """Register artifact hash for deduplication."""
    content_hash = get_content_hash(content, url)
    artifact_hashes.add(content_hash)
    return content_hash


def get_session_history(session_id: str, max_messages: int = 20) -> list[dict]:
    """Get conversation history for a session."""
    if session_id not in sessions:
        sessions[session_id] = []
    return sessions[session_id][-max_messages:]


def add_to_session(session_id: str, role: str, content: str):
    """Add message to session history."""
    # Don't store empty messages
    if not content or not content.strip():
        return

    if session_id not in sessions:
        sessions[session_id] = []
    sessions[session_id].append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    })
    # Keep only last 40 messages (20 turns)
    sessions[session_id] = sessions[session_id][-40:]


# ============================================================================
# RAG System Prompts
# ============================================================================

CHAT_SYSTEM_PROMPT = """You are the AI Horizon Research Assistant, an expert on how AI is transforming the cybersecurity workforce. You help users understand job impacts, career planning, and workforce trends.

## Knowledge Base
You have access to:
1. **DCWF Reference Data** - The Department of Defense Cyber Workforce Framework (~1,350 tasks across 52 work roles)
2. **Classified Artifacts** - Research papers, videos, and articles analyzed for AI workforce impact

## Classification Framework
- **Replace** (🔴): AI will fully automate this task (>70% AI capability)
- **Augment** (🟡): AI assists but humans remain essential (40-70% AI)
- **Remain Human** (🟢): Must stay human (ethics, legal, accountability, judgment)
- **New Task** (🔵): AI creates new work not in traditional DCWF

## Response Format
Structure your responses with clear sections when appropriate:

**📋 Summary**: Brief answer to the question

**🎯 Relevant DCWF Tasks**: List specific task IDs and names
- Task 1234: Description (Classification)
- Task 5678: Description (Classification)

**📊 Evidence**: Cite specific sources from the knowledge base

**💡 Recommendations**: Actionable advice for the user

**🔗 Related Topics**: Suggest follow-up questions

## Guidelines
- Always cite specific DCWF task IDs when discussing job impacts
- Be encouraging - frame AI as an opportunity for skill evolution, not just displacement
- Be balanced - acknowledge uncertainty and conflicting evidence
- Be specific - avoid vague statements; use data and examples
- Keep responses focused but comprehensive

If asked about submitting evidence, explain users can share URLs (YouTube, articles) or paste content directly for AI classification.
"""

CLASSIFICATION_PROMPT = """Analyze this artifact and classify its impact on cybersecurity workforce tasks using the DCWF framework.

ARTIFACT:
Title: {title}
Source Type: {source_type}
Content: {content}

## IMPORTANT: First determine if this content is relevant to cybersecurity or DCWF tasks.
Content is relevant if it discusses ANY of these topics:
- Cybersecurity, information security, network security
- AI/automation impact on security jobs or tasks
- Threat detection, incident response, vulnerability management
- Security operations, SOC, SIEM, threat intelligence
- Penetration testing, ethical hacking, security engineering
- Compliance, risk management, security governance
- Any DCWF (DoD Cyber Workforce Framework) work roles or tasks

If the content is NOT about cybersecurity/DCWF, set is_relevant to false.

## Classification Categories (only if relevant)
- **Replace**: AI will fully automate this task (>70% AI capability)
- **Augment**: AI assists but humans remain essential (40-70% AI)
- **Remain Human**: Must stay human due to ethics, legal, or accountability
- **New Task**: AI enables new capabilities not in traditional DCWF

## Scoring Criteria
- **Relevance** (0-1): How relevant is this to cybersecurity/DCWF? (< 0.3 = not relevant)
- **Credibility** (0-1): Source reliability, author expertise, peer review status
- **Impact** (0-1): Significance of the finding to workforce transformation
- **Specificity** (0-1): How clearly it maps to specific DCWF tasks

Respond with this exact JSON structure:
{{
    "is_relevant": true,
    "relevance_score": 0.85,
    "relevance_reason": "Brief explanation of why this is/isn't relevant to cybersecurity",
    "classification": "Replace|Augment|Remain Human|New Task",
    "confidence": 0.85,
    "credibility_score": 0.8,
    "impact_score": 0.7,
    "specificity_score": 0.9,
    "rationale": "2-3 sentence explanation of classification decision",
    "dcwf_tasks": [
        {{
            "task_id": "1234",
            "task_name": "Name of the task",
            "relevance_score": 0.9,
            "impact_description": "How AI impacts this specific task"
        }}
    ],
    "work_roles": ["Cyber Defense Analyst", "Security Architect"],
    "key_findings": [
        "Key finding 1 from the artifact",
        "Key finding 2 from the artifact"
    ],
    "ai_tools_mentioned": ["ChatGPT", "GitHub Copilot"],
    "evidence_strength": "strong|moderate|weak"
}}

If content is NOT relevant, return:
{{
    "is_relevant": false,
    "relevance_score": 0.1,
    "relevance_reason": "This content is about [topic], not cybersecurity or DCWF tasks",
    "classification": null,
    "confidence": 0,
    "rationale": "Content not relevant to cybersecurity workforce analysis"
}}
"""


# ============================================================================
# API Endpoints
# ============================================================================

# Serve static files (UI)
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def serve_ui():
    """Serve the main UI."""
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"error": "UI not found", "path": str(index_path)}


@app.get("/api/health")
async def health():
    """Health check and API info."""
    import os
    return {
        "name": "AI Horizon API",
        "version": "1.0.0",
        "status": "healthy",
        "gemini_configured": client is not None,
        "evidence_count": len(evidence_store),
        "supabase_configured": bool(os.getenv("SUPABASE_URL")) and bool(os.getenv("SUPABASE_SERVICE_KEY")),
        "stores": {
            "dcwf": DCWF_STORE_NAME is not None,
            "artifacts": ARTIFACTS_STORE_NAME is not None,
        }
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    RAG-powered chat endpoint.

    Uses local evidence store + Gemini File Search to ground responses.
    Local RAG flow:
    1. Check for evidence-related keywords/DCWF task IDs in the query
    2. If found, retrieve relevant artifacts from local evidence_store.json
    3. Inject retrieved context into the system prompt
    4. Call Gemini with augmented prompt
    5. If Gemini fails, return friendly message with evidence count
    """
    if not client:
        raise HTTPException(status_code=500, detail="Gemini client not configured")

    # Get or create session
    session_id = request.session_id or str(uuid.uuid4())
    history = get_session_history(session_id)

    # Current message
    current_message = request.message.strip() if request.message else ""
    if not current_message:
        return ChatResponse(
            output="Please enter a message.",
            session_id=session_id,
            sources=[],
        )

    # =========================================================================
    # LOCAL RAG: Search evidence store for relevant context
    # =========================================================================
    local_context = ""
    relevant_evidence = []

    if detect_evidence_query(current_message):
        relevant_evidence = search_evidence_store(current_message, limit=5)
        if relevant_evidence:
            local_context = build_context_from_evidence(relevant_evidence)
            logger.info(f"Found {len(relevant_evidence)} relevant artifacts for query: {current_message[:50]}...")

    # Build augmented system prompt with local context
    augmented_system_prompt = CHAT_SYSTEM_PROMPT
    if local_context:
        augmented_system_prompt += local_context

    # Build conversation contents (filter out empty messages)
    contents = []
    for msg in history:
        msg_content = msg.get("content", "")
        if msg_content and msg_content.strip():  # Skip empty messages
            role = "user" if msg["role"] == "user" else "model"
            contents.append(types.Content(
                role=role,
                parts=[types.Part(text=msg_content)]
            ))

    # Add current message
    contents.append(types.Content(
        role="user",
        parts=[types.Part(text=current_message)]
    ))

    # Build File Search tools
    stores = []
    if DCWF_STORE_NAME:
        stores.append(DCWF_STORE_NAME)
    if ARTIFACTS_STORE_NAME:
        stores.append(ARTIFACTS_STORE_NAME)

    tools = []
    if stores:
        tools.append(types.Tool(
            file_search=types.FileSearch(
                file_search_store_names=stores
            )
        ))

    # Generate response with retry logic
    try:
        config = types.GenerateContentConfig(
            system_instruction=augmented_system_prompt,
        )
        if tools:
            config.tools = tools

        def make_chat_request(c):
            return c.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                config=config,
            )

        response = call_with_retry(make_chat_request)

        # Safely extract text from response
        assistant_message = ""
        if response and hasattr(response, 'text'):
            assistant_message = response.text or ""

        # Handle empty response - use fallback with local evidence
        if not assistant_message.strip():
            if relevant_evidence:
                # Provide evidence-based fallback
                evidence_summary = f"I found {len(relevant_evidence)} piece(s) of evidence related to your query:\n\n"
                for i, ev in enumerate(relevant_evidence, 1):
                    evidence_summary += f"**{i}. {ev.get('title', 'Untitled')}**\n"
                    evidence_summary += f"   - Classification: {ev.get('classification', 'Unknown')}\n"
                    if ev.get('rationale'):
                        evidence_summary += f"   - Summary: {(ev.get('rationale') or '')[:200]}...\n"
                    evidence_summary += "\n"
                assistant_message = f"I couldn't generate a full response right now, but here's what I found in our evidence store:\n\n{evidence_summary}"
            else:
                assistant_message = "I apologize, but I couldn't generate a response. This may be due to API rate limits. Please try again in a moment."

        # Update session history
        add_to_session(session_id, "user", request.message)
        add_to_session(session_id, "assistant", assistant_message)

        # Extract sources from local evidence
        sources = [ev.get('source_url') for ev in relevant_evidence if ev.get('source_url')]

        return ChatResponse(
            output=assistant_message,
            session_id=session_id,
            sources=sources,
        )

    except RateLimitError as e:
        logger.warning(f"Chat rate limited: {e}")
        # Provide evidence-based fallback on rate limit
        if relevant_evidence:
            evidence_summary = f"I'm currently rate-limited, but I found {len(relevant_evidence)} piece(s) of evidence related to your query:\n\n"
            for i, ev in enumerate(relevant_evidence, 1):
                evidence_summary += f"**{i}. {ev.get('title', 'Untitled')}** ({ev.get('classification', 'Unknown')})\n"
                if ev.get('rationale'):
                    evidence_summary += f"   {(ev.get('rationale') or '')[:150]}...\n"
            evidence_summary += "\nPlease try again in a minute for a full AI-generated response."
            return ChatResponse(
                output=evidence_summary,
                session_id=session_id,
                sources=[ev.get('source_url') for ev in relevant_evidence if ev.get('source_url')],
            )
        return ChatResponse(
            output="I'm currently experiencing high demand. The free tier API limit (20 requests/minute) has been reached. Please wait a minute and try again.",
            session_id=session_id,
            sources=[],
        )

    except Exception as e:
        logger.error(f"Chat error: {e}")
        error_str = str(e).lower()

        # Provide evidence-based fallback on errors
        if relevant_evidence:
            evidence_summary = f"I encountered an issue, but I found {len(relevant_evidence)} piece(s) of evidence related to your query:\n\n"
            for i, ev in enumerate(relevant_evidence, 1):
                evidence_summary += f"**{i}. {ev.get('title', 'Untitled')}** ({ev.get('classification', 'Unknown')})\n"
                if ev.get('rationale'):
                    evidence_summary += f"   {(ev.get('rationale') or '')[:150]}...\n"
            evidence_summary += "\nPlease try again for a full AI-generated response."
            return ChatResponse(
                output=evidence_summary,
                session_id=session_id,
                sources=[ev.get('source_url') for ev in relevant_evidence if ev.get('source_url')],
            )

        # Return user-friendly error for rate limits (backup check)
        if "429" in error_str or "quota" in error_str or "rate" in error_str:
            return ChatResponse(
                output="I'm currently experiencing high demand. The free tier API limit (20 requests/minute) has been reached. Please wait a minute and try again.",
                session_id=session_id,
                sources=[],
            )

        # Return user-friendly error for 400 bad request errors
        if "400" in error_str or "invalid_argument" in error_str or "bad request" in error_str:
            return ChatResponse(
                output="I encountered an issue processing your request. This can happen if the conversation history became corrupted. Please try clearing your browser's local storage (F12 → Application → Local Storage → Clear) and refreshing the page.",
                session_id=session_id,
                sources=[],
            )

        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/search")
async def search_get(
    query: Optional[str] = None,
    job_role: Optional[str] = None,
    dcwf_task: Optional[str] = None,
    ai_tool: Optional[str] = None,
    classification: Optional[str] = None,
    limit: int = 20,
):
    """Search DCWF tasks and evidence (GET version for frontend)."""
    # Convert to SearchRequest and call the main search function
    class_type = None
    if classification:
        try:
            class_type = ClassificationType(classification)
        except ValueError:
            pass

    request = SearchRequest(
        query=query,
        job_role=job_role,
        dcwf_task=dcwf_task,
        ai_tool=ai_tool,
        classification=class_type,
        limit=min(limit, 100),
    )
    return await search_post(request)


def count_evidence_for_task(task_id: str) -> int:
    """Count how many artifacts in our evidence store relate to a specific DCWF task."""
    count = 0
    task_id_upper = task_id.upper()

    for artifact in evidence_store:
        dcwf_tasks = artifact.get("dcwf_tasks", [])
        for task in dcwf_tasks:
            artifact_task_id = task.get("task_id", "") if isinstance(task, dict) else str(task)
            if task_id_upper in artifact_task_id.upper():
                count += 1
                break  # Count each artifact only once per task
    return count


def search_local_evidence(query: str, filters: dict, limit: int = 20) -> list[dict]:
    """
    Search local evidence store first, then optionally augment with Gemini.
    This provides faster results and accurate evidence counts.
    """
    query_lower = query.lower().strip() if query else ""
    query_words = query_lower.split() if query_lower else []

    # Extract unique DCWF tasks from all evidence
    task_map = {}  # task_id -> task info with evidence count

    for artifact in evidence_store:
        # Check filters
        if filters.get("classification"):
            if artifact.get("classification", "").lower() != filters["classification"].lower():
                continue

        if filters.get("job_role"):
            role_match = False
            work_roles = artifact.get("work_roles", [])
            work_role = artifact.get("work_role", "")
            if filters["job_role"].lower() in work_role.lower():
                role_match = True
            for wr in work_roles:
                if filters["job_role"].lower() in wr.lower():
                    role_match = True
                    break
            if not role_match:
                continue

        if filters.get("ai_tool"):
            tool_match = False
            ai_tools = artifact.get("ai_tools_mentioned", [])
            for tool in ai_tools:
                if filters["ai_tool"].lower() in tool.lower():
                    tool_match = True
                    break
            if not tool_match:
                continue

        # Extract DCWF tasks from this artifact
        dcwf_tasks = artifact.get("dcwf_tasks", [])
        for task in dcwf_tasks:
            if isinstance(task, dict):
                task_id = task.get("task_id", "")
                task_name = task.get("task_name", "")
                impact = task.get("impact_description", "")
            else:
                task_id = str(task)
                task_name = ""
                impact = ""

            if not task_id:
                continue

            # Check DCWF task filter
            if filters.get("dcwf_task"):
                if filters["dcwf_task"].upper() not in task_id.upper():
                    continue

            # Check if task matches query (if query provided)
            # Allow partial word matching for better UX
            if query_words:
                searchable = " ".join([
                    task_id.lower(),
                    task_name.lower(),
                    impact.lower(),
                    artifact.get("title", "").lower(),
                    artifact.get("rationale", "").lower(),
                    (artifact.get("content") or "")[:2000].lower(),
                    " ".join(artifact.get("key_findings", [])).lower(),
                ])
                # Check if ANY query word matches
                if not any(word in searchable for word in query_words):
                    continue

            if task_id not in task_map:
                task_map[task_id] = {
                    "task_id": task_id,
                    "task_name": task_name or f"Task {task_id}",
                    "description": impact or (artifact.get("rationale") or "")[:200],
                    "classification": artifact.get("classification", "Augment"),
                    "confidence": artifact.get("confidence", 0.7),
                    "evidence_count": 1,
                    "work_roles": list(artifact.get("work_roles", [])),
                }
            else:
                # Increment evidence count for this task
                task_map[task_id]["evidence_count"] += 1
                # Merge work roles
                for role in artifact.get("work_roles", []):
                    if role not in task_map[task_id]["work_roles"]:
                        task_map[task_id]["work_roles"].append(role)

    # Convert to list and sort by evidence count
    results = list(task_map.values())
    results.sort(key=lambda x: x["evidence_count"], reverse=True)

    return results[:limit]


@app.post("/api/search")
async def search_post(request: SearchRequest):
    """
    Search DCWF tasks and evidence.

    Supports filtering by:
    - Free text query
    - Job role
    - DCWF task ID
    - AI tool
    - Classification type

    Uses local evidence store first for accurate evidence counts,
    then falls back to Gemini File Search if needed.
    """
    # Build filters dict
    filters = {
        "job_role": request.job_role,
        "dcwf_task": request.dcwf_task,
        "ai_tool": request.ai_tool,
        "classification": request.classification.value if request.classification else None,
    }

    query = request.query or ""

    # First, search local evidence store
    local_results = search_local_evidence(query, filters, request.limit)

    # If we have local results, return them
    if local_results:
        search_query = f"{query} {' '.join(f'{k}:{v}' for k, v in filters.items() if v)}"
        return {"results": local_results, "query": search_query.strip(), "source": "local"}

    # Fall back to Gemini File Search if no local results
    if not client:
        return {"results": [], "query": query, "message": "No results found in local store and Gemini not configured"}

    # Build search query for Gemini
    query_parts = []
    if query:
        query_parts.append(query)
    if request.job_role:
        query_parts.append(f"job role: {request.job_role}")
    if request.dcwf_task:
        query_parts.append(f"DCWF task: {request.dcwf_task}")
    if request.ai_tool:
        query_parts.append(f"AI tool: {request.ai_tool}")
    if request.classification:
        query_parts.append(f"classification: {request.classification.value}")

    if not query_parts:
        query_parts.append("list cybersecurity tasks impacted by AI")

    search_query = " ".join(query_parts)

    # Expand search with semantic correlations
    search_query = expand_search_terms(search_query)

    # Use File Search for RAG query
    stores = []
    if DCWF_STORE_NAME:
        stores.append(DCWF_STORE_NAME)
    if ARTIFACTS_STORE_NAME:
        stores.append(ARTIFACTS_STORE_NAME)

    try:
        # Note: Can't use response_mime_type with File Search tools
        search_prompt = f"""Search the knowledge base for: {search_query}

Return results as a JSON array with this exact format (no markdown, just raw JSON):
[
    {{
        "task_id": "1234",
        "task_name": "Short name",
        "description": "What this task involves",
        "classification": "Replace|Augment|Remain Human|New Task",
        "confidence": 0.85,
        "evidence_count": 0,
        "work_roles": ["Role 1"]
    }}
]

Return up to {request.limit} most relevant results."""

        def make_search_request(c):
            return c.models.generate_content(
                model=GEMINI_MODEL,
                contents=search_prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(
                        file_search=types.FileSearch(
                            file_search_store_names=stores
                        )
                    )] if stores else None,
                ),
            )

        response = call_with_retry(make_search_request)

        # Parse results - try to extract JSON from response
        response_text = response.text or ""
        if not response_text.strip():
            return {"results": [], "query": search_query, "message": "No results found"}

        try:
            # Try to find JSON array in response
            json_match = re.search(r'\[[\s\S]*\]', response_text)
            if json_match:
                results = json.loads(json_match.group())
            else:
                results = json.loads(response_text)

            # Update evidence counts from local store
            for result in results:
                if result.get("task_id"):
                    result["evidence_count"] = count_evidence_for_task(result["task_id"])

        except json.JSONDecodeError:
            # If JSON parsing fails, return structured response
            results = [{"raw_response": response_text}]

        return {"results": results, "query": search_query, "source": "gemini"}

    except RateLimitError as e:
        logger.warning(f"Search rate limited: {e}")
        return {"results": [], "query": search_query, "error": "Rate limit reached. Please wait a minute and try again."}

    except Exception as e:
        logger.error(f"Search error: {e}")
        error_str = str(e).lower()
        if "429" in error_str or "quota" in error_str or "rate" in error_str:
            return {"results": [], "query": search_query, "error": "Rate limit reached. Please wait a minute and try again."}
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/submit", response_model=SubmitArtifactResponse)
async def submit_artifact(
    request: SubmitArtifactRequest,
    background_tasks: BackgroundTasks
):
    """
    Submit new evidence/artifact for classification.

    Workflow:
    1. Check URL for duplicates (before extracting)
    2. Extract content (if URL provided)
    3. Check content for duplicates
    4. Classify using AI
    5. Store in Gemini File Search
    6. Return classification result
    """
    if not client:
        raise HTTPException(status_code=500, detail="Gemini client not configured")

    # Early URL duplicate check (before extraction to save API calls)
    if request.url:
        existing = check_url_exists(str(request.url))
        if existing:
            return SubmitArtifactResponse(
                success=False,
                artifact_id=existing.get("artifact_id"),
                is_duplicate=True,
                is_relevant=True,  # Existing entries were relevant
                stored=False,  # Not stored again
                message=f"This URL was already submitted on {existing.get('stored_at', 'unknown date')}. Classification: {existing.get('classification', 'Unknown')}",
                classification={
                    "classification": existing.get("classification"),
                    "confidence": existing.get("confidence"),
                    "rationale": existing.get("rationale"),
                }
            )

    # Determine content
    content = request.content
    title = request.title

    if request.url and not content:
        # Extract content from URL
        url_str = str(request.url)

        # Check for YouTube
        if "youtube.com" in url_str or "youtu.be" in url_str:
            try:
                from src.extraction.router import extract_youtube
                content = extract_youtube(url_str)
                title = title or f"YouTube Video: {url_str}"
                request.source_type = "youtube"
                logger.info(f"Extracted YouTube transcript: {len(content)} chars")
            except Exception as e:
                logger.error(f"YouTube extraction failed: {e}")
                raise HTTPException(status_code=400, detail=f"Could not extract YouTube transcript: {e}")
        else:
            # Use trafilatura for web extraction
            try:
                from src.extraction.router import extract_web
                content = extract_web(url_str)
                title = title or f"Web Article: {url_str}"
                logger.info(f"Extracted web content: {len(content)} chars")
            except Exception as e:
                logger.error(f"Web extraction failed: {e}")
                raise HTTPException(status_code=400, detail=f"Could not extract web content: {e}")
    
    if not content:
        raise HTTPException(status_code=400, detail="No content or URL provided")

    # Generate title for text-only submissions if not already set
    if not title and content:
        # Extract first meaningful sentence or first 50 chars
        first_line = content.strip().split('\n')[0][:100]
        if len(first_line) > 50:
            title = f"Text: {first_line[:50]}..."
        else:
            title = f"Text: {first_line}"

    # Check for content duplicates (hash-based)
    if check_duplicate(content, str(request.url) if request.url else None):
        return SubmitArtifactResponse(
            success=False,
            is_duplicate=True,
            is_relevant=True,  # Existing entries were relevant
            stored=False,  # Not stored again
            message="This content has already been submitted and classified."
        )
    
    # Generate artifact ID
    artifact_id = f"artifact_{uuid.uuid4().hex[:12]}"
    
    # Classify the artifact with retry logic
    try:
        classification_prompt = CLASSIFICATION_PROMPT.format(
            title=title or "Untitled",
            source_type=request.source_type,
            content=content[:30000],  # Limit content length
        )

        def make_classification_request(c):
            return c.models.generate_content(
                model=GEMINI_MODEL,
                contents=classification_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )

        classification_response = call_with_retry(make_classification_request)
        classification = json.loads(classification_response.text)

    except Exception as e:
        logger.error(f"Classification error: {e}")
        classification = {
            "is_relevant": True,  # Assume relevant if classification fails
            "relevance_score": 0.5,
            "classification": "Augment",
            "confidence": 0.5,
            "rationale": "Auto-classification failed, defaulting to Augment",
            "error": str(e)
        }

    # Check relevance - if not relevant to cybersecurity/DCWF, don't store
    is_relevant = classification.get("is_relevant", True)
    relevance_score = classification.get("relevance_score", 1.0)
    relevance_reason = classification.get("relevance_reason", "")

    # Threshold: relevance_score < 0.3 means not relevant enough
    RELEVANCE_THRESHOLD = 0.3

    if not is_relevant or relevance_score < RELEVANCE_THRESHOLD:
        logger.info(f"Content not relevant (score: {relevance_score}): {relevance_reason}")
        return SubmitArtifactResponse(
            success=True,  # Classification succeeded, just not stored
            artifact_id=None,
            is_duplicate=False,
            is_relevant=False,
            relevance_score=relevance_score,
            relevance_reason=relevance_reason or "This content doesn't appear to be related to cybersecurity or DCWF tasks.",
            stored=False,
            message=f"Content analyzed but not stored. {relevance_reason or 'This content does not appear to be related to cybersecurity or DCWF workforce tasks.'}",
            classification=classification
        )

    # Register for deduplication (only for relevant content)
    register_artifact(content, str(request.url) if request.url else None)

    # Auto-detect resource type from source_type
    detected_resource_type = request.resource_type
    if not detected_resource_type:
        if request.source_type == "youtube":
            detected_resource_type = ResourceType.VIDEO
        elif request.source_type == "pdf":
            detected_resource_type = ResourceType.RESOURCE
        else:
            detected_resource_type = ResourceType.ARTICLE

    # Auto-detect difficulty based on content keywords
    detected_difficulty = request.difficulty
    if not detected_difficulty:
        content_lower = content.lower()
        if any(kw in content_lower for kw in ["advanced", "expert", "senior", "architect"]):
            detected_difficulty = DifficultyLevel.ADVANCED
        elif any(kw in content_lower for kw in ["intermediate", "mid-level", "professional"]):
            detected_difficulty = DifficultyLevel.INTERMEDIATE
        else:
            detected_difficulty = DifficultyLevel.BEGINNER

    # Save to local evidence store (for local RAG)
    artifact_data = {
        "artifact_id": artifact_id,
        "title": title or "Untitled",
        "content": content[:5000],  # Store first 5000 chars for context
        "source_url": str(request.url) if request.url else None,
        "source_type": request.source_type,
        "resource_type": detected_resource_type.value if detected_resource_type else "Article",
        "difficulty": detected_difficulty.value if detected_difficulty else "Beginner",
        "is_free": request.is_free,
        "work_role": request.work_role or (classification.get("work_roles", [None])[0] if classification.get("work_roles") else None),
        "classification": classification.get("classification"),
        "confidence": classification.get("confidence"),
        "rationale": classification.get("rationale"),
        "dcwf_tasks": classification.get("dcwf_tasks", []),
        "work_roles": classification.get("work_roles", []),
        "key_findings": classification.get("key_findings", []),
        "ai_tools_mentioned": classification.get("ai_tools_mentioned", []),
        "stored_at": datetime.now().isoformat(),
    }
    try:
        add_to_evidence_store(artifact_data)
        logger.info(f"Successfully added artifact {artifact_id} to evidence store")
    except Exception as e:
        logger.error(f"Failed to add artifact {artifact_id} to evidence store: {e}")

    # Store in File Search (background task)
    if ARTIFACTS_STORE_NAME:
        background_tasks.add_task(
            store_artifact_in_file_search,
            artifact_id=artifact_id,
            title=title or "Untitled",
            content=content,
            source_url=str(request.url) if request.url else None,
            source_type=request.source_type,
            classification=classification,
        )

    return SubmitArtifactResponse(
        success=True,
        artifact_id=artifact_id,
        is_duplicate=False,
        is_relevant=True,
        relevance_score=relevance_score,
        relevance_reason=relevance_reason,
        stored=True,
        message=f"Artifact classified as '{classification.get('classification')}' with {classification.get('confidence', 0):.0%} confidence.",
        classification=classification,
    )


@app.post("/api/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
):
    """
    Upload a file (PDF, DOCX, TXT, etc.) for classification.
    """
    if not client:
        raise HTTPException(status_code=500, detail="Gemini client not configured")

    # Get file extension
    filename = file.filename or "uploaded_file"
    ext = Path(filename).suffix.lower()

    # Read file content
    file_content = await file.read()

    # Extract text based on file type
    content = None
    source_type = "document"

    try:
        if ext == ".pdf":
            # Save to temp file and extract
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(file_content)
                tmp_path = tmp.name

            try:
                from src.extraction.router import extract_pdf
                content = extract_pdf(Path(tmp_path))
                source_type = "pdf"
            finally:
                os.unlink(tmp_path)

        elif ext in (".docx", ".doc"):
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                tmp.write(file_content)
                tmp_path = tmp.name

            try:
                from src.extraction.router import extract_docx
                content = extract_docx(Path(tmp_path))
                source_type = "document"
            finally:
                os.unlink(tmp_path)

        elif ext in (".txt", ".md"):
            content = file_content.decode("utf-8")
            source_type = "text"

        elif ext in (".xlsx", ".xls"):
            # For Excel, we'll just note it's not supported yet
            raise HTTPException(status_code=400, detail="Excel files not yet supported. Please copy/paste the relevant content.")

        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File extraction failed: {e}")
        raise HTTPException(status_code=400, detail=f"Could not extract content from file: {e}")

    if not content or len(content.strip()) < 50:
        raise HTTPException(status_code=400, detail="Could not extract sufficient text from file")

    # Check for duplicates
    if check_duplicate(content, filename):
        return SubmitArtifactResponse(
            success=False,
            is_duplicate=True,
            message="This content has already been submitted and classified."
        )

    # Generate artifact ID
    artifact_id = f"artifact_{uuid.uuid4().hex[:12]}"
    title = title or filename

    # Classify the artifact with retry logic
    try:
        classification_prompt = CLASSIFICATION_PROMPT.format(
            title=title,
            source_type=source_type,
            content=content[:30000],
        )

        def make_classification_request(c):
            return c.models.generate_content(
                model=GEMINI_MODEL,
                contents=classification_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )

        classification_response = call_with_retry(make_classification_request)
        classification = json.loads(classification_response.text)

    except Exception as e:
        logger.error(f"Classification error: {e}")
        classification = {
            "classification": "Augment",
            "confidence": 0.5,
            "rationale": "Auto-classification failed, defaulting to Augment",
            "error": str(e)
        }

    # Register for deduplication
    register_artifact(content, filename)

    # Auto-detect resource type from file type
    detected_resource_type = ResourceType.RESOURCE
    if source_type == "pdf":
        detected_resource_type = ResourceType.RESOURCE
    elif source_type == "document":
        detected_resource_type = ResourceType.ARTICLE

    # Auto-detect difficulty based on content keywords
    content_lower = content.lower()
    if any(kw in content_lower for kw in ["advanced", "expert", "senior", "architect"]):
        detected_difficulty = DifficultyLevel.ADVANCED
    elif any(kw in content_lower for kw in ["intermediate", "mid-level", "professional"]):
        detected_difficulty = DifficultyLevel.INTERMEDIATE
    else:
        detected_difficulty = DifficultyLevel.BEGINNER

    # Save to local evidence store (for local RAG)
    artifact_data = {
        "artifact_id": artifact_id,
        "title": title,
        "content": content[:5000],  # Store first 5000 chars for context
        "source_url": None,
        "source_type": source_type,
        "resource_type": detected_resource_type.value,
        "difficulty": detected_difficulty.value,
        "is_free": True,  # Uploaded files are considered free
        "work_role": classification.get("work_roles", [None])[0] if classification.get("work_roles") else None,
        "classification": classification.get("classification"),
        "confidence": classification.get("confidence"),
        "rationale": classification.get("rationale"),
        "dcwf_tasks": classification.get("dcwf_tasks", []),
        "work_roles": classification.get("work_roles", []),
        "key_findings": classification.get("key_findings", []),
        "ai_tools_mentioned": classification.get("ai_tools_mentioned", []),
        "stored_at": datetime.now().isoformat(),
    }
    add_to_evidence_store(artifact_data)

    # Store in File Search (background task)
    if ARTIFACTS_STORE_NAME:
        background_tasks.add_task(
            store_artifact_in_file_search,
            artifact_id=artifact_id,
            title=title,
            content=content,
            source_url=None,
            source_type=source_type,
            classification=classification,
        )

    return SubmitArtifactResponse(
        success=True,
        artifact_id=artifact_id,
        is_duplicate=False,
        message=f"Artifact classified as '{classification.get('classification')}' with {classification.get('confidence', 0):.0%} confidence.",
        classification=classification,
    )


async def store_artifact_in_file_search(
    artifact_id: str,
    title: str,
    content: str,
    source_url: Optional[str],
    source_type: str,
    classification: dict,
):
    """Background task to store artifact in Gemini File Search."""
    import tempfile
    
    artifact_data = {
        "artifact_id": artifact_id,
        "title": title,
        "content": content,
        "source_url": source_url,
        "source_type": source_type,
        "classification": classification.get("classification"),
        "confidence": classification.get("confidence"),
        "rationale": classification.get("rationale"),
        "dcwf_tasks": classification.get("dcwf_tasks", []),
        "work_roles": classification.get("work_roles", []),
        "key_findings": classification.get("key_findings", []),
        "stored_at": datetime.now().isoformat(),
    }
    
    # Write to temp file and upload
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(artifact_data, f)
        temp_path = f.name
    
    try:
        operation = client.file_search_stores.upload_to_file_search_store(
            file=temp_path,
            file_search_store_name=ARTIFACTS_STORE_NAME,
            config={"display_name": f"{title} ({artifact_id})"},
        )
        logger.info(f"Stored artifact {artifact_id}: {operation}")
    except Exception as e:
        logger.error(f"Failed to store artifact {artifact_id}: {e}")
    finally:
        os.unlink(temp_path)


@app.get("/api/evidence/artifact/{artifact_id}")
async def get_artifact_detail(artifact_id: str):
    """
    Get a single artifact by its artifact_id.
    Used by frontend evidence detail page.
    """
    # Search local evidence store for the artifact
    for artifact in evidence_store:
        if artifact.get("artifact_id") == artifact_id:
            return {
                "artifact_id": artifact.get("artifact_id"),
                "title": artifact.get("title", "Untitled"),
                "content": (artifact.get("content") or "")[:2000],  # Limit content for response
                "source_url": artifact.get("source_url"),
                "source_type": artifact.get("source_type", "web"),
                "resource_type": artifact.get("resource_type", "Article"),
                "difficulty": artifact.get("difficulty", "Beginner"),
                "is_free": artifact.get("is_free", True),
                "work_role": artifact.get("work_role"),
                "work_roles": artifact.get("work_roles", []),
                "classification": artifact.get("classification", "Augment"),
                "confidence": artifact.get("confidence", 0.7),
                "rationale": artifact.get("rationale", ""),
                "dcwf_tasks": artifact.get("dcwf_tasks", []),
                "key_findings": artifact.get("key_findings", []),
                "ai_tools_mentioned": artifact.get("ai_tools_mentioned", []),
                "stored_at": artifact.get("stored_at", ""),
            }

    raise HTTPException(status_code=404, detail=f"Artifact {artifact_id} not found")


@app.get("/api/evidence/{task_id}")
async def get_evidence(task_id: str):
    """
    Get all evidence/social proof for a specific DCWF task.
    """
    if not client:
        raise HTTPException(status_code=500, detail="Gemini client not configured")
    
    stores = []
    if ARTIFACTS_STORE_NAME:
        stores.append(ARTIFACTS_STORE_NAME)
    
    if not stores:
        return {"task_id": task_id, "evidence": [], "message": "No artifact store configured"}
    
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=f"""Find all evidence and artifacts related to DCWF task {task_id}.

Return as JSON array:
[
    {{
        "artifact_id": "id",
        "title": "Title",
        "source_url": "URL or null",
        "source_type": "web|youtube|pdf|article",
        "classification": "Replace|Augment|Remain Human|New Task",
        "confidence": 0.0-1.0,
        "rationale": "Brief explanation",
        "retrieved_on": "ISO date"
    }}
]""",
            config=types.GenerateContentConfig(
                tools=[types.Tool(
                    file_search=types.FileSearch(
                        file_search_store_names=stores
                    )
                )],
                response_mime_type="application/json",
            ),
        )
        
        evidence = json.loads(response.text)
        return {"task_id": task_id, "evidence": evidence}
        
    except Exception as e:
        logger.error(f"Evidence lookup error: {e}")
        return {"task_id": task_id, "evidence": [], "error": str(e)}


@app.get("/api/roles")
async def list_roles():
    """Get list of all DCWF work roles for dropdown."""
    # This would query your DCWF store
    # For now, return common cybersecurity roles
    roles = [
        {"id": "AN-TWA", "name": "Threat/Warning Analyst", "category": "Analyze"},
        {"id": "AN-ASA", "name": "All-Source Analyst", "category": "Analyze"},
        {"id": "AN-EXP", "name": "Exploitation Analyst", "category": "Analyze"},
        {"id": "AN-TGT", "name": "Target Developer", "category": "Analyze"},
        {"id": "AN-LNG", "name": "Multi-Disciplined Language Analyst", "category": "Analyze"},
        {"id": "CO-CLO", "name": "Cyber Operations Planner", "category": "Collect and Operate"},
        {"id": "CO-OPL", "name": "Partner Integration Planner", "category": "Collect and Operate"},
        {"id": "IN-FOR", "name": "Cyber Crime Investigator", "category": "Investigate"},
        {"id": "IN-INV", "name": "Cyber Defense Forensics Analyst", "category": "Investigate"},
        {"id": "OM-ADM", "name": "System Administrator", "category": "Operate and Maintain"},
        {"id": "OM-NET", "name": "Network Operations Specialist", "category": "Operate and Maintain"},
        {"id": "OM-STS", "name": "Technical Support Specialist", "category": "Operate and Maintain"},
        {"id": "OV-MGT", "name": "Information Systems Security Manager", "category": "Oversee and Govern"},
        {"id": "OV-EXL", "name": "Executive Cyber Leadership", "category": "Oversee and Govern"},
        {"id": "PR-CDA", "name": "Cyber Defense Analyst", "category": "Protect and Defend"},
        {"id": "PR-CIR", "name": "Cyber Defense Incident Responder", "category": "Protect and Defend"},
        {"id": "PR-INF", "name": "Cyber Defense Infrastructure Support", "category": "Protect and Defend"},
        {"id": "PR-VAM", "name": "Vulnerability Assessment Analyst", "category": "Protect and Defend"},
        {"id": "SP-ARC", "name": "Security Architect", "category": "Securely Provision"},
        {"id": "SP-DEV", "name": "Secure Software Developer", "category": "Securely Provision"},
        {"id": "SP-RSK", "name": "Risk Analyst", "category": "Securely Provision"},
        {"id": "SP-SYS", "name": "Information Systems Security Developer", "category": "Securely Provision"},
    ]
    return {"roles": roles}


@app.get("/api/stats")
async def get_stats():
    """Get statistics about the knowledge base."""
    # Count from local evidence store
    classification_counts = {"replace": 0, "augment": 0, "remain_human": 0, "new_task": 0}
    free_count = 0
    resource_types = {}
    difficulty_counts = {"Beginner": 0, "Intermediate": 0, "Advanced": 0, "Expert": 0}

    for artifact in evidence_store:
        classification = (artifact.get("classification") or "").lower().replace(" ", "_")
        if classification in classification_counts:
            classification_counts[classification] += 1

        if artifact.get("is_free", True):
            free_count += 1

        rt = artifact.get("resource_type", "Article")
        resource_types[rt] = resource_types.get(rt, 0) + 1

        diff = artifact.get("difficulty", "Beginner")
        if diff in difficulty_counts:
            difficulty_counts[diff] += 1

    return {
        "total_tasks": 1350,  # From DCWF data
        "total_resources": len(evidence_store),
        "free_resources": free_count,
        "classified_artifacts": len(artifact_hashes),
        "classifications": classification_counts,
        "resource_types": resource_types,
        "difficulty_levels": difficulty_counts,
        "last_updated": datetime.now().isoformat(),
    }


@app.get("/api/resources")
async def list_resources(
    role: Optional[str] = None,
    resource_type: Optional[str] = None,
    difficulty: Optional[str] = None,
    is_free: Optional[bool] = None,
    dcwf_task: Optional[str] = None,
    classification: Optional[str] = None,
    query: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
):
    """
    List all learning resources with optional filters and pagination.
    Similar to theaihorizon.org/resources page.

    Args:
        role: Filter by work role
        resource_type: Filter by resource type (Video, Course, etc.)
        difficulty: Filter by difficulty level
        is_free: Filter by free/premium
        dcwf_task: Filter by DCWF task ID
        classification: Filter by classification (Replace, Augment, Remain Human, New Task)
        query: Text search in title and rationale
        page: Page number (1-indexed)
        limit: Items per page (default 20, max 100)
    """
    # Validate pagination params
    limit = min(max(1, limit), 100)  # Clamp between 1 and 100
    page = max(1, page)  # Minimum page is 1
    offset = (page - 1) * limit

    results = []

    for artifact in evidence_store:
        # Apply filters
        if role and role.lower() not in (artifact.get("work_role") or "").lower():
            # Also check work_roles list
            work_roles = artifact.get("work_roles", [])
            if not any(role.lower() in wr.lower() for wr in work_roles):
                continue

        if resource_type and artifact.get("resource_type") != resource_type:
            continue

        if difficulty and artifact.get("difficulty") != difficulty:
            continue

        if is_free is not None and artifact.get("is_free", True) != is_free:
            continue

        # DCWF task filter
        if dcwf_task:
            dcwf_tasks = artifact.get("dcwf_tasks", [])
            task_ids = [t.get("task_id", "") for t in dcwf_tasks]
            if not any(dcwf_task.upper() in tid.upper() for tid in task_ids):
                continue

        # Classification filter
        if classification:
            artifact_cls = artifact.get("classification", "")
            if classification.lower() != artifact_cls.lower():
                continue

        # Text search in title and rationale
        if query:
            title = (artifact.get("title") or "").lower()
            rationale = (artifact.get("rationale") or "").lower()
            query_lower = query.lower()
            if query_lower not in title and query_lower not in rationale:
                continue

        results.append({
            "artifact_id": artifact.get("artifact_id"),
            "title": artifact.get("title"),
            "source_url": artifact.get("source_url"),
            "resource_type": artifact.get("resource_type", "Article"),
            "difficulty": artifact.get("difficulty", "Beginner"),
            "is_free": artifact.get("is_free", True),
            "work_role": artifact.get("work_role"),
            "work_roles": artifact.get("work_roles", []),
            "classification": artifact.get("classification"),
            "confidence": artifact.get("confidence"),
            "rationale": (artifact.get("rationale") or "")[:200],
            "stored_at": artifact.get("stored_at"),
        })

    # Sort by most recent first
    results.sort(key=lambda x: x.get("stored_at") or "", reverse=True)

    # Calculate pagination
    total = len(results)
    total_pages = (total + limit - 1) // limit  # Ceiling division
    paginated_results = results[offset:offset + limit]

    return {
        "resources": paginated_results,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
        "filters": {
            "role": role,
            "resource_type": resource_type,
            "difficulty": difficulty,
            "is_free": is_free,
        }
    }


@app.get("/api/skills")
async def list_skills():
    """
    List all skills/work roles with resource counts.
    Similar to theaihorizon.org/skills page.
    """
    # Group resources by work role
    role_stats = {}

    for artifact in evidence_store:
        work_roles = artifact.get("work_roles", [])
        if artifact.get("work_role"):
            work_roles = [artifact.get("work_role")] + work_roles

        for role in work_roles:
            if role not in role_stats:
                role_stats[role] = {
                    "name": role,
                    "total_resources": 0,
                    "free_resources": 0,
                    "classifications": {"Replace": 0, "Augment": 0, "Remain Human": 0, "New Task": 0},
                }
            role_stats[role]["total_resources"] += 1
            if artifact.get("is_free", True):
                role_stats[role]["free_resources"] += 1
            classification = artifact.get("classification", "Augment")
            if classification in role_stats[role]["classifications"]:
                role_stats[role]["classifications"][classification] += 1

    # Convert to list and add role metadata from /api/roles
    skills = []
    role_metadata = {
        "Threat/Warning Analyst": {"id": "AN-TWA", "category": "Analyze", "priority": "High Priority"},
        "Cyber Defense Analyst": {"id": "PR-CDA", "category": "Protect and Defend", "priority": "Critical Priority"},
        "Security Analyst": {"id": "PR-CDA", "category": "Protect and Defend", "priority": "Critical Priority"},
        "Security Architect": {"id": "SP-ARC", "category": "Securely Provision", "priority": "High Priority"},
        "Penetration Tester": {"id": "PR-VAM", "category": "Protect and Defend", "priority": "High Priority"},
        "Vulnerability Assessment Analyst": {"id": "PR-VAM", "category": "Protect and Defend", "priority": "High Priority"},
        "Cyber Defense Incident Responder": {"id": "PR-CIR", "category": "Protect and Defend", "priority": "Critical Priority"},
        "System Administrator": {"id": "OM-ADM", "category": "Operate and Maintain", "priority": "High Priority"},
        "Network Operations Specialist": {"id": "OM-NET", "category": "Operate and Maintain", "priority": "High Priority"},
        "Secure Software Developer": {"id": "SP-DEV", "category": "Securely Provision", "priority": "High Priority"},
        "Risk Analyst": {"id": "SP-RSK", "category": "Securely Provision", "priority": "Moderate Priority"},
    }

    for role_name, stats in role_stats.items():
        metadata = role_metadata.get(role_name)
        if metadata:
            role_id = metadata["id"]
            category = metadata["category"]
            priority = metadata["priority"]
        else:
            # Generate unique ID for unknown roles based on role name
            slug = role_name.lower().replace(" ", "-").replace("/", "-")
            role_id = f"UNK-{slug[:8].upper()}"
            category = "Other"
            priority = "Moderate Priority"

        skills.append({
            "name": role_name,
            "id": role_id,
            "category": category,
            "priority": priority,
            "total_resources": stats["total_resources"],
            "free_resources": stats["free_resources"],
            "classifications": stats["classifications"],
            "slug": role_name.lower().replace(" ", "-").replace("/", "-"),
        })

    # Sort by resource count
    skills.sort(key=lambda x: x["total_resources"], reverse=True)

    return {"skills": skills, "total": len(skills)}


# ============================================================================
# Admin Endpoints
# ============================================================================

@app.delete("/api/admin/cleanup-incomplete")
async def cleanup_incomplete_records():
    """
    Delete records from Supabase that have no artifact_id or source_url.
    These are incomplete submissions that clutter the database.
    """
    try:
        from src.api.supabase_client import get_supabase
        client = get_supabase()

        # Delete records where source_url is empty or null
        response = client.table("document_registry").delete().or_(
            "source_url.is.null,source_url.eq."
        ).execute()

        deleted_count = len(response.data) if response.data else 0

        # Reload the evidence store
        load_evidence_store()

        return {
            "success": True,
            "deleted_count": deleted_count,
            "message": f"Deleted {deleted_count} incomplete records"
        }
    except Exception as e:
        logger.error(f"Cleanup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/admin/delete-artifact/{artifact_id}")
async def delete_artifact_by_id(artifact_id: str):
    """Delete a specific artifact by its artifact_id (format: artifact_XXXX or raw UUID)."""
    try:
        from src.api.supabase_client import get_supabase
        client = get_supabase()

        # The artifact_id is formatted as "artifact_<first12chars_of_uuid>"
        # We need to find the record by matching the start of the UUID
        if artifact_id.startswith("artifact_"):
            uuid_prefix = artifact_id.replace("artifact_", "")
            # Search for records where id starts with this prefix
            response = client.table("document_registry").select("id").execute()
            matching_id = None
            for row in response.data:
                if row["id"].startswith(uuid_prefix):
                    matching_id = row["id"]
                    break

            if not matching_id:
                raise HTTPException(status_code=404, detail=f"Artifact {artifact_id} not found")

            # Delete by actual UUID
            delete_response = client.table("document_registry").delete().eq("id", matching_id).execute()
            deleted_count = len(delete_response.data) if delete_response.data else 0
        else:
            # Assume it's a raw UUID
            response = client.table("document_registry").delete().eq("id", artifact_id).execute()
            deleted_count = len(response.data) if response.data else 0

        if deleted_count == 0:
            raise HTTPException(status_code=404, detail=f"Artifact {artifact_id} not found")

        # Reload the evidence store
        load_evidence_store()

        return {
            "success": True,
            "deleted_artifact_id": artifact_id,
            "message": f"Deleted artifact {artifact_id}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete artifact error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/admin/cleanup-untitled")
async def cleanup_untitled_artifacts():
    """Delete all artifacts with 'Untitled' as their title."""
    try:
        from src.api.supabase_client import get_supabase
        client = get_supabase()

        # Find and delete all untitled records
        response = client.table("document_registry").delete().eq("file_name", "Untitled").execute()
        deleted_count = len(response.data) if response.data else 0

        # Reload the evidence store
        load_evidence_store()

        return {
            "success": True,
            "deleted_count": deleted_count,
            "message": f"Deleted {deleted_count} untitled artifact(s)"
        }
    except Exception as e:
        logger.error(f"Cleanup untitled error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
