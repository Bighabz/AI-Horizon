"""URL-based deduplication against the existing evidence store.

Checks both the PostgreSQL document_registry (primary store) and the local
evidence_store.json fallback, using the same URL normalization rules as
src/api/main.py (lowercase, no fragment, no trailing slash, no www prefix).
"""

import json
import logging
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from src.ingestion.models import IngestionCandidate

logger = logging.getLogger(__name__)

# Same location the API uses (repo backend root / evidence_store.json).
EVIDENCE_STORE_PATH = Path(__file__).parent.parent.parent / "evidence_store.json"


def normalize_url(url: str) -> str:
    """Normalize a URL for comparison (mirrors normalize_url in src/api/main.py)."""
    if not url:
        return ""
    url = url.strip().lower()
    parsed = urlparse(url)
    url = url.split("#")[0]
    url = url.rstrip("/")
    if parsed.netloc.startswith("www."):
        url = url.replace("://www.", "://", 1)
    return url


def load_json_store_urls(store_path: Optional[Path] = None) -> set[str]:
    """Normalized source URLs from the local evidence_store.json (empty set if absent)."""
    path = Path(store_path) if store_path else EVIDENCE_STORE_PATH
    if not path.exists():
        return set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            artifacts = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Could not read evidence store {path}: {e}")
        return set()

    urls = set()
    for artifact in artifacts:
        url = artifact.get("source_url") or artifact.get("url")
        if url:
            urls.add(normalize_url(url))
    return urls


def load_db_urls() -> set[str]:
    """Normalized source URLs from PostgreSQL (empty set if the DB is unreachable)."""
    try:
        from src.api.db import get_all_source_urls
    except Exception as e:  # pragma: no cover - psycopg2 missing etc.
        logger.warning(f"Database module unavailable, skipping DB dedupe: {e}")
        return set()

    # get_all_source_urls() already returns an empty set on connection errors.
    return {normalize_url(u) for u in get_all_source_urls()}


def load_existing_urls(include_db: bool = True, store_path: Optional[Path] = None) -> set[str]:
    """All known artifact URLs (normalized) from Postgres and/or the JSON store."""
    urls = load_json_store_urls(store_path)
    if include_db:
        urls |= load_db_urls()
    logger.info(f"Loaded {len(urls)} existing URL(s) for deduplication")
    return urls


def filter_new(
    candidates: list[IngestionCandidate], existing_urls: set[str]
) -> tuple[list[IngestionCandidate], list[IngestionCandidate]]:
    """Split candidates into (new, duplicates) by normalized URL.

    Also dedupes within the batch itself (the same story syndicated by two
    feeds only counts once).
    """
    new: list[IngestionCandidate] = []
    duplicates: list[IngestionCandidate] = []
    seen_in_batch: set[str] = set()

    for candidate in candidates:
        normalized = normalize_url(candidate.source_url)
        if normalized in existing_urls or normalized in seen_in_batch:
            duplicates.append(candidate)
        else:
            seen_in_batch.add(normalized)
            new.append(candidate)

    return new, duplicates
