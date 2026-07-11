"""Offline tests for RSS/Atom fetching and parsing (fixture XML, no network)."""

import pytest

from src.ingestion import fetcher
from src.ingestion.models import FeedSource


class TestLoadFeedSources:
    def test_default_feeds_load(self):
        sources = fetcher.load_feed_sources()
        assert len(sources) >= 3
        for source in sources:
            assert source.name
            assert source.url.startswith("http")
            assert source.enabled is True

    def test_disabled_feeds_are_skipped(self, tmp_path):
        feeds_file = tmp_path / "feeds.json"
        feeds_file.write_text(
            '{"feeds": ['
            '{"name": "On", "url": "https://on.example/feed"},'
            '{"name": "Off", "url": "https://off.example/feed", "enabled": false}'
            "]}",
            encoding="utf-8",
        )
        sources = fetcher.load_feed_sources(feeds_file)
        assert [s.name for s in sources] == ["On"]


class TestParseRss:
    def test_parses_all_items(self, rss_xml):
        entries = fetcher.parse_feed(rss_xml, "Example Security Feed")
        assert len(entries) == 4  # includes the linkless item; normalizer drops it later

    def test_fields(self, rss_xml):
        entries = fetcher.parse_feed(rss_xml, "Example Security Feed")
        first = entries[0]
        assert first.feed_name == "Example Security Feed"
        assert first.title == "AI Agents Take Over SOC Triage"
        assert first.link == "https://example.com/articles/ai-soc-triage"
        assert first.published == "Wed, 08 Jul 2026 09:00:00 +0000"
        assert first.guid == "https://example.com/articles/ai-soc-triage"
        # content:encoded captured separately from description
        assert "threat hunting" in first.content
        assert "AI agents" in first.summary or "AI agents" in first.content

    def test_linkless_item_has_no_link(self, rss_xml):
        entries = fetcher.parse_feed(rss_xml, "f")
        assert entries[3].link is None


class TestParseAtom:
    def test_parses_entries(self, atom_xml):
        entries = fetcher.parse_feed(atom_xml, "Example Atom Security Feed")
        assert len(entries) == 2

    def test_prefers_alternate_link(self, atom_xml):
        entries = fetcher.parse_feed(atom_xml, "f")
        assert entries[0].link == "https://atom.example.org/blog/prompt-injection"
        assert entries[1].link == "https://atom.example.org/blog/zero-trust-machine-identity"

    def test_published_falls_back_to_updated(self, atom_xml):
        entries = fetcher.parse_feed(atom_xml, "f")
        assert entries[0].published == "2026-07-09T09:15:00Z"
        assert entries[1].published == "2026-07-08T16:45:00Z"


class TestParseErrors:
    def test_invalid_xml_raises(self):
        with pytest.raises(ValueError, match="Invalid feed XML"):
            fetcher.parse_feed("this is not xml <", "bad")

    def test_unrecognized_root_raises(self):
        with pytest.raises(ValueError, match="Unrecognized feed format"):
            fetcher.parse_feed("<html><body>nope</body></html>", "bad")


class TestFetchFeed:
    def test_fetch_uses_requests_with_headers_and_timeout(self, monkeypatch):
        import requests

        calls = {}

        class FakeResponse:
            text = "<rss version='2.0'><channel></channel></rss>"

            def raise_for_status(self):
                calls["raised_checked"] = True

        def fake_get(url, headers=None, timeout=None):
            calls["url"] = url
            calls["headers"] = headers
            calls["timeout"] = timeout
            return FakeResponse()

        monkeypatch.setattr(requests, "get", fake_get)

        source = FeedSource(name="Fake", url="https://fake.example/feed")
        text = fetcher.fetch_feed(source)

        assert "rss" in text
        assert calls["url"] == "https://fake.example/feed"
        assert "AIHorizonIngest" in calls["headers"]["User-Agent"]
        assert calls["timeout"] == fetcher.FETCH_TIMEOUT_SECONDS
        assert calls["raised_checked"] is True
