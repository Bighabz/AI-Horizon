"""RSS/Atom feed fetching and parsing.

Uses stdlib ``xml.etree.ElementTree`` (feedparser is not a project dependency)
and ``requests`` (already a dependency) for HTTP. Supports RSS 2.0 and Atom.
"""

import json
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

from src.ingestion.models import FeedEntry, FeedSource

logger = logging.getLogger(__name__)

DEFAULT_FEEDS_PATH = Path(__file__).parent / "feeds.json"
USER_AGENT = "AIHorizonIngest/1.0 (+https://theaihorizon.org)"
FETCH_TIMEOUT_SECONDS = 20

ATOM_NS = "{http://www.w3.org/2005/Atom}"
CONTENT_NS = "{http://purl.org/rss/1.0/modules/content/}"


def load_feed_sources(path: Optional[Path] = None) -> list[FeedSource]:
    """Load feed sources from a feeds.json file (enabled feeds only)."""
    feeds_path = Path(path) if path else DEFAULT_FEEDS_PATH
    with open(feeds_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    sources = [FeedSource(**feed) for feed in data.get("feeds", [])]
    enabled = [s for s in sources if s.enabled]
    logger.info(f"Loaded {len(enabled)} enabled feed(s) from {feeds_path}")
    return enabled


def fetch_feed(source: FeedSource, timeout: int = FETCH_TIMEOUT_SECONDS) -> str:
    """Fetch the raw XML for a feed. Raises on HTTP errors."""
    import requests  # local import keeps parsing usable fully offline

    response = requests.get(
        source.url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml"},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.text


def parse_feed(xml_text: str, feed_name: str) -> list[FeedEntry]:
    """Parse RSS 2.0 or Atom XML into FeedEntry objects.

    Raises ValueError for XML that is not a recognized feed format.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise ValueError(f"Invalid feed XML for '{feed_name}': {e}") from e

    tag = root.tag.lower()
    if tag == "rss" or tag.endswith("}rss"):
        return _parse_rss(root, feed_name)
    if tag == f"{ATOM_NS}feed".lower() or root.tag == f"{ATOM_NS}feed":
        return _parse_atom(root, feed_name)
    raise ValueError(f"Unrecognized feed format for '{feed_name}' (root element: {root.tag})")


def _text(element: Optional[ET.Element]) -> str:
    """Full text of an element including nested markup text, stripped."""
    if element is None:
        return ""
    return "".join(element.itertext()).strip()


def _parse_rss(root: ET.Element, feed_name: str) -> list[FeedEntry]:
    """Parse an RSS 2.0 document."""
    channel = root.find("channel")
    if channel is None:
        raise ValueError(f"RSS feed '{feed_name}' has no <channel> element")

    entries = []
    for item in channel.findall("item"):
        link = (item.findtext("link") or "").strip() or None
        entries.append(
            FeedEntry(
                feed_name=feed_name,
                title=(item.findtext("title") or "").strip(),
                link=link,
                summary=_text(item.find("description")),
                content=_text(item.find(f"{CONTENT_NS}encoded")),
                published=(item.findtext("pubDate") or "").strip() or None,
                guid=(item.findtext("guid") or "").strip() or None,
            )
        )
    logger.info(f"Parsed {len(entries)} RSS item(s) from '{feed_name}'")
    return entries


def _atom_link(entry: ET.Element) -> Optional[str]:
    """Pick the best link from an Atom entry (prefer rel='alternate')."""
    links = entry.findall(f"{ATOM_NS}link")
    for link in links:
        if link.get("rel", "alternate") == "alternate" and link.get("href"):
            return link.get("href")
    for link in links:
        if link.get("href"):
            return link.get("href")
    return None


def _parse_atom(root: ET.Element, feed_name: str) -> list[FeedEntry]:
    """Parse an Atom document."""
    entries = []
    for entry in root.findall(f"{ATOM_NS}entry"):
        published = (
            entry.findtext(f"{ATOM_NS}published") or entry.findtext(f"{ATOM_NS}updated") or ""
        ).strip() or None
        entries.append(
            FeedEntry(
                feed_name=feed_name,
                title=_text(entry.find(f"{ATOM_NS}title")),
                link=_atom_link(entry),
                summary=_text(entry.find(f"{ATOM_NS}summary")),
                content=_text(entry.find(f"{ATOM_NS}content")),
                published=published,
                guid=(entry.findtext(f"{ATOM_NS}id") or "").strip() or None,
            )
        )
    logger.info(f"Parsed {len(entries)} Atom entr(y/ies) from '{feed_name}'")
    return entries
