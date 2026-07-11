"""Data models for the feed ingestion pipeline."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

# The endpoint stores the first 5000 chars of content (see src/api/main.py),
# and sends at most 30000 chars to the classifier.
MAX_CONTENT_CHARS = 30000
STORED_CONTENT_CHARS = 5000


class FeedSource(BaseModel):
    """A configured RSS/Atom feed (one entry in feeds.json)."""

    name: str = Field(description="Human-readable feed name")
    url: str = Field(description="Feed URL (RSS 2.0 or Atom)")
    enabled: bool = Field(default=True, description="Skip the feed when False")


class FeedEntry(BaseModel):
    """A single raw entry parsed from an RSS/Atom feed."""

    feed_name: str = Field(description="Name of the feed this entry came from")
    title: str = Field(default="", description="Entry title")
    link: Optional[str] = Field(default=None, description="Canonical article URL")
    summary: str = Field(default="", description="Short summary/description (may contain HTML)")
    content: str = Field(default="", description="Full content if provided (may contain HTML)")
    published: Optional[str] = Field(default=None, description="Published date string as-is")
    guid: Optional[str] = Field(default=None, description="Feed-provided unique id")


class IngestionCandidate(BaseModel):
    """A normalized feed entry, shaped like a pipeline submission.

    Mirrors the inputs of the existing `/api/submit` endpoint (title, content,
    url, source_type) so the non-dry path can route straight into the existing
    classification + storage entry points.
    """

    title: str
    content: str = Field(description="Plain-text content (HTML stripped)")
    source_url: str
    source_type: str = Field(default="web")
    resource_type: str = Field(default="Article")
    feed_name: str = Field(default="")
    published: Optional[str] = Field(default=None)

    def to_artifact_preview(self) -> dict:
        """Preview of the evidence-store artifact this candidate would become.

        Matches the schema written by the existing pipeline (see the
        `artifact_data` dict in `/api/submit` and `evidence_store.json`).
        Classification fields are None/empty because Gemini has not run yet.
        """
        return {
            "artifact_id": None,  # assigned at ingestion time (uuid4)
            "title": self.title,
            "content": self.content[:STORED_CONTENT_CHARS],
            "source_url": self.source_url,
            "source_type": self.source_type,
            "resource_type": self.resource_type,
            "difficulty": None,  # auto-detected at classification time
            "is_free": True,
            "work_role": None,
            "submission_type": "evidence",
            "classification": None,
            "confidence": None,
            "rationale": None,
            "dcwf_tasks": [],
            "work_roles": [],
            "key_findings": [],
            "ai_tools_mentioned": [],
            "stored_at": None,
        }


class CollectStats(BaseModel):
    """Statistics from one collection run."""

    feeds_configured: int = 0
    feeds_fetched: int = 0
    feeds_failed: int = 0
    entries_fetched: int = 0
    entries_normalized: int = 0
    errors: list[str] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=datetime.now)
