"""Offline tests for the ingestion normalizer (feed entry -> artifact shape)."""

from src.ingestion import fetcher, normalizer
from src.ingestion.models import MAX_CONTENT_CHARS, STORED_CONTENT_CHARS, FeedEntry


class TestStripHtml:
    def test_removes_tags_and_unescapes_entities(self):
        assert normalizer.strip_html("<p>Alerts &amp; enrichment</p>") == "Alerts & enrichment"

    def test_drops_script_content(self):
        text = normalizer.strip_html("<p>safe</p><script>evil()</script><p>also safe</p>")
        assert "evil" not in text
        assert "safe" in text and "also safe" in text

    def test_collapses_whitespace(self):
        assert normalizer.strip_html("a\n\n   b\t c") == "a b c"

    def test_plain_text_with_entities(self):
        assert normalizer.strip_html("Phishing &amp; Deepfakes") == "Phishing & Deepfakes"

    def test_empty(self):
        assert normalizer.strip_html("") == ""


class TestNormalizeEntry:
    def _entry(self, **kwargs) -> FeedEntry:
        defaults = dict(
            feed_name="Fixture Feed",
            title="A Title",
            link="https://example.com/post",
            summary="<p>A summary</p>",
            content="",
            published="Wed, 08 Jul 2026 09:00:00 +0000",
        )
        defaults.update(kwargs)
        return FeedEntry(**defaults)

    def test_basic_normalization(self):
        candidate = normalizer.normalize_entry(self._entry())
        assert candidate is not None
        assert candidate.title == "A Title"
        assert candidate.content == "A summary"
        assert candidate.source_url == "https://example.com/post"
        assert candidate.source_type == "web"
        assert candidate.resource_type == "Article"
        assert candidate.feed_name == "Fixture Feed"
        assert candidate.published == "Wed, 08 Jul 2026 09:00:00 +0000"

    def test_full_content_preferred_over_summary(self):
        candidate = normalizer.normalize_entry(
            self._entry(content="<p>Full body text</p>", summary="<p>short</p>")
        )
        assert candidate.content == "Full body text"

    def test_entry_without_link_is_dropped(self):
        assert normalizer.normalize_entry(self._entry(link=None)) is None
        assert normalizer.normalize_entry(self._entry(link="   ")) is None

    def test_entry_with_no_title_and_no_content_is_dropped(self):
        assert normalizer.normalize_entry(self._entry(title="", summary="", content="")) is None

    def test_untitled_entry_gets_web_article_title(self):
        candidate = normalizer.normalize_entry(self._entry(title=""))
        assert candidate.title == "Web Article: https://example.com/post"

    def test_content_is_truncated(self):
        candidate = normalizer.normalize_entry(self._entry(summary="x" * (MAX_CONTENT_CHARS + 500)))
        assert len(candidate.content) == MAX_CONTENT_CHARS


class TestArtifactShape:
    # Schema written by /api/submit and stored in evidence_store.json / Postgres.
    EXPECTED_KEYS = {
        "artifact_id",
        "title",
        "content",
        "source_url",
        "source_type",
        "resource_type",
        "difficulty",
        "is_free",
        "work_role",
        "submission_type",
        "classification",
        "confidence",
        "rationale",
        "dcwf_tasks",
        "work_roles",
        "key_findings",
        "ai_tools_mentioned",
        "stored_at",
    }

    def test_preview_matches_pipeline_schema(self):
        entry = FeedEntry(
            feed_name="f", title="t", link="https://e.example/x", summary="s" * 6000
        )
        candidate = normalizer.normalize_entry(entry)
        preview = candidate.to_artifact_preview()
        assert set(preview.keys()) == self.EXPECTED_KEYS
        assert preview["source_type"] == "web"
        assert preview["resource_type"] == "Article"
        assert preview["submission_type"] == "evidence"
        assert len(preview["content"]) <= STORED_CONTENT_CHARS


class TestEndToEndFixtures:
    def test_rss_fixture_normalizes_dropping_linkless(self, rss_xml):
        entries = fetcher.parse_feed(rss_xml, "Example Security Feed")
        candidates = normalizer.normalize_entries(entries)
        assert len(candidates) == 3  # 4 items minus the linkless one
        urls = {c.source_url for c in candidates}
        assert "https://example.com/articles/ai-soc-triage" in urls
        # HTML/CDATA content became plain text, script dropped
        triage = next(c for c in candidates if "triage" in c.source_url)
        assert "<" not in triage.content
        assert "evil()" not in triage.content

    def test_atom_fixture_normalizes(self, atom_xml):
        entries = fetcher.parse_feed(atom_xml, "Example Atom Security Feed")
        candidates = normalizer.normalize_entries(entries)
        assert len(candidates) == 2
        assert candidates[0].content == (
            "Researchers demonstrated prompt injection attacks that exfiltrate data "
            "from enterprise copilots."
        )
