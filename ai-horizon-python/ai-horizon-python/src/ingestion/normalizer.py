"""Normalize raw feed entries into pipeline-shaped ingestion candidates.

The output shape mirrors what the existing `/api/submit` endpoint accepts
(title, content, url, source_type) so downstream classification/storage can be
reused unchanged.
"""

import html
import logging
import re
from html.parser import HTMLParser
from typing import Optional

from src.ingestion.models import MAX_CONTENT_CHARS, FeedEntry, IngestionCandidate

logger = logging.getLogger(__name__)

# Entries with less text than this are still ingested (the classifier sees the
# URL/title too), but empty-link or empty-title-and-content entries are dropped.
_WHITESPACE_RE = re.compile(r"\s+")


class _HTMLTextExtractor(HTMLParser):
    """Collects text content from HTML, skipping script/style blocks."""

    _SKIPPED_TAGS = {"script", "style"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in self._SKIPPED_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIPPED_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self._parts.append(data)

    def text(self) -> str:
        return " ".join(self._parts)


def strip_html(raw: str) -> str:
    """Convert an HTML fragment to collapsed plain text."""
    if not raw:
        return ""
    if "<" in raw:
        extractor = _HTMLTextExtractor()
        extractor.feed(raw)
        text = extractor.text()
    else:
        text = html.unescape(raw)
    return _WHITESPACE_RE.sub(" ", text).strip()


def normalize_entry(entry: FeedEntry) -> Optional[IngestionCandidate]:
    """Convert a FeedEntry into an IngestionCandidate.

    Returns None (and logs) for entries that cannot become artifacts:
    missing link, or no usable title/content at all.
    """
    if not entry.link or not entry.link.strip():
        logger.warning(f"Skipping entry without link from '{entry.feed_name}': {entry.title!r}")
        return None

    link = entry.link.strip()
    title = strip_html(entry.title)
    # Prefer full content over summary, like the extraction pipeline prefers
    # full article text over metadata.
    content = strip_html(entry.content) or strip_html(entry.summary)

    if not title and not content:
        logger.warning(f"Skipping empty entry from '{entry.feed_name}': {link}")
        return None

    if not title:
        # Same convention as /api/submit for untitled web articles.
        title = f"Web Article: {link}"

    return IngestionCandidate(
        title=title,
        content=content[:MAX_CONTENT_CHARS],
        source_url=link,
        source_type="web",
        resource_type="Article",
        feed_name=entry.feed_name,
        published=entry.published,
    )


def normalize_entries(entries: list[FeedEntry]) -> list[IngestionCandidate]:
    """Normalize a batch of entries, dropping unusable ones."""
    candidates = []
    for entry in entries:
        candidate = normalize_entry(entry)
        if candidate is not None:
            candidates.append(candidate)
    return candidates
