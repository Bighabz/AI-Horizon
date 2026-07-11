"""Ingestion pipeline: fetch -> normalize -> dedupe -> classify/store.

The dry-run path (collect + dedupe) is fully offline apart from the public
feed fetches and never imports the API app, Gemini client, or database.
The real path routes candidates into the existing classification entry point
(the same prompt/retry/storage machinery as POST /api/submit).
"""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.ingestion import dedupe, fetcher, normalizer
from src.ingestion.models import CollectStats, FeedSource, IngestionCandidate, STORED_CONTENT_CHARS

logger = logging.getLogger(__name__)

RELEVANCE_THRESHOLD = 0.3  # same gate as /api/submit


def collect_candidates(
    sources: list[FeedSource],
) -> tuple[list[IngestionCandidate], CollectStats]:
    """Fetch and normalize all enabled feeds; one bad feed never aborts the run."""
    stats = CollectStats(feeds_configured=len(sources))
    candidates: list[IngestionCandidate] = []

    for source in sources:
        try:
            xml_text = fetcher.fetch_feed(source)
            entries = fetcher.parse_feed(xml_text, source.name)
        except Exception as e:
            stats.feeds_failed += 1
            stats.errors.append(f"{source.name}: {e}")
            logger.error(f"Feed '{source.name}' failed: {e}")
            continue

        stats.feeds_fetched += 1
        stats.entries_fetched += len(entries)
        candidates.extend(normalizer.normalize_entries(entries))

    stats.entries_normalized = len(candidates)
    return candidates, stats


def run_ingestion(
    feeds_path: Optional[Path] = None,
    limit: Optional[int] = None,
    include_db: bool = True,
) -> dict:
    """Fetch, normalize, and dedupe. Returns everything a caller needs to
    either preview (dry-run) or ingest for real."""
    sources = fetcher.load_feed_sources(feeds_path)
    candidates, stats = collect_candidates(sources)
    existing_urls = dedupe.load_existing_urls(include_db=include_db)
    new, duplicates = dedupe.filter_new(candidates, existing_urls)

    if limit is not None and limit >= 0:
        new = new[:limit]

    return {
        "stats": stats,
        "existing_url_count": len(existing_urls),
        "new": new,
        "duplicates": duplicates,
    }


def _detect_difficulty(content: str) -> str:
    """Keyword-based difficulty detection (mirrors /api/submit)."""
    content_lower = content.lower()
    if any(kw in content_lower for kw in ["advanced", "expert", "senior", "architect"]):
        return "Advanced"
    if any(kw in content_lower for kw in ["intermediate", "mid-level", "professional"]):
        return "Intermediate"
    return "Beginner"


def ingest_candidate(candidate: IngestionCandidate) -> dict:
    """Classify one candidate with Gemini and store it via the existing pipeline.

    This is the REAL path: it requires GEMINI_API_KEY (and DATABASE_URL for
    Postgres persistence). It reuses the classification prompt, retry/key
    rotation, and evidence-store writers from src/api/main.py so ingested
    artifacts are byte-for-byte the same shape as user submissions.
    """
    import json as _json

    from src.api import main as api  # heavy import; deliberately not at module level

    if not api.API_KEYS:
        raise RuntimeError("GEMINI_API_KEY is not configured; cannot classify. Use --dry-run.")

    prompt = api.CLASSIFICATION_PROMPT.format(
        title=candidate.title,
        source_type=candidate.source_type,
        content=candidate.content[:30000],
    )

    def make_classification_request(client):
        return client.models.generate_content(
            model=api.GEMINI_MODEL,
            contents=prompt,
            config=api.types.GenerateContentConfig(response_mime_type="application/json"),
        )

    response = api.call_with_retry(make_classification_request)
    classification = _json.loads(response.text)

    is_relevant = classification.get("is_relevant", True)
    relevance_score = classification.get("relevance_score", 1.0)
    if not is_relevant or relevance_score < RELEVANCE_THRESHOLD:
        logger.info(
            f"Not relevant (score {relevance_score}): {candidate.source_url} - "
            f"{classification.get('relevance_reason', '')}"
        )
        return {
            "stored": False,
            "reason": classification.get("relevance_reason", "not relevant"),
            "source_url": candidate.source_url,
        }

    artifact_id = f"artifact_{uuid.uuid4().hex[:12]}"
    artifact_data = {
        "artifact_id": artifact_id,
        "title": candidate.title,
        "content": candidate.content[:STORED_CONTENT_CHARS],
        "source_url": candidate.source_url,
        "source_type": candidate.source_type,
        "resource_type": candidate.resource_type,
        "difficulty": _detect_difficulty(candidate.content),
        "is_free": True,
        "work_role": (classification.get("work_roles") or [None])[0],
        "submission_type": classification.get("submission_type", "evidence"),
        "classification": classification.get("classification"),
        "confidence": classification.get("confidence"),
        "rationale": classification.get("rationale"),
        "dcwf_tasks": classification.get("dcwf_tasks", []),
        "work_roles": classification.get("work_roles", []),
        "key_findings": classification.get("key_findings", []),
        "ai_tools_mentioned": classification.get("ai_tools_mentioned", []),
        "stored_at": datetime.now().isoformat(),
    }

    api.add_to_evidence_store(artifact_data)
    logger.info(f"Ingested {artifact_id}: {candidate.title[:60]}")
    return {
        "stored": True,
        "artifact_id": artifact_id,
        "classification": artifact_data["classification"],
        "confidence": artifact_data["confidence"],
        "source_url": candidate.source_url,
    }
