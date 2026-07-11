"""Offline tests for URL deduplication against the existing evidence store."""

from src.ingestion import dedupe, fetcher, normalizer
from src.ingestion.models import IngestionCandidate


def _candidate(url: str, title: str = "t") -> IngestionCandidate:
    return IngestionCandidate(title=title, content="c", source_url=url)


class TestNormalizeUrl:
    def test_equivalent_variants_normalize_identically(self):
        variants = [
            "https://example.com/articles/existing-story",
            "https://www.example.com/articles/existing-story/",
            "HTTPS://EXAMPLE.COM/ARTICLES/EXISTING-STORY",
            "https://example.com/articles/existing-story#section",
            "https://example.com/articles/existing-story/",
        ]
        normalized = {dedupe.normalize_url(v) for v in variants}
        assert normalized == {"https://example.com/articles/existing-story"}

    def test_empty(self):
        assert dedupe.normalize_url("") == ""

    def test_scheme_difference_is_preserved(self):
        assert dedupe.normalize_url("http://example.com/a") != dedupe.normalize_url(
            "https://example.com/a"
        )


class TestLoadExistingUrls:
    def test_json_store_urls(self, evidence_store_path):
        urls = dedupe.load_json_store_urls(evidence_store_path)
        assert urls == {"https://example.com/articles/existing-story"}

    def test_missing_store_is_empty(self, tmp_path):
        assert dedupe.load_json_store_urls(tmp_path / "nope.json") == set()

    def test_corrupt_store_is_empty(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        assert dedupe.load_json_store_urls(bad) == set()

    def test_db_urls_are_merged_and_normalized(self, monkeypatch, evidence_store_path):
        import src.api.db as db

        monkeypatch.setattr(
            db, "get_all_source_urls", lambda: {"https://www.db.example/post/"}
        )
        urls = dedupe.load_existing_urls(include_db=True, store_path=evidence_store_path)
        assert "https://db.example/post" in urls
        assert "https://example.com/articles/existing-story" in urls

    def test_include_db_false_never_touches_db(self, monkeypatch, evidence_store_path):
        import src.api.db as db

        def boom():
            raise AssertionError("DB must not be queried when include_db=False")

        monkeypatch.setattr(db, "get_all_source_urls", boom)
        urls = dedupe.load_existing_urls(include_db=False, store_path=evidence_store_path)
        assert urls == {"https://example.com/articles/existing-story"}


class TestFilterNew:
    def test_existing_url_variant_is_duplicate(self):
        existing = {"https://example.com/articles/existing-story"}
        new, dupes = dedupe.filter_new(
            [_candidate("https://www.example.com/articles/existing-story/")], existing
        )
        assert new == []
        assert len(dupes) == 1

    def test_in_batch_duplicates_collapse(self):
        new, dupes = dedupe.filter_new(
            [
                _candidate("https://a.example/1"),
                _candidate("https://A.EXAMPLE/1/".lower()),
                _candidate("https://a.example/2"),
            ],
            set(),
        )
        assert [c.source_url for c in new] == ["https://a.example/1", "https://a.example/2"]
        assert len(dupes) == 1

    def test_all_new_when_store_empty(self):
        new, dupes = dedupe.filter_new([_candidate("https://a.example/1")], set())
        assert len(new) == 1 and dupes == []


class TestFixtureEndToEnd:
    def test_rss_fixture_dedupes_against_fixture_store(self, rss_xml, evidence_store_path):
        """Full offline pipeline: parse -> normalize -> dedupe."""
        entries = fetcher.parse_feed(rss_xml, "Example Security Feed")
        candidates = normalizer.normalize_entries(entries)
        existing = dedupe.load_existing_urls(include_db=False, store_path=evidence_store_path)
        new, dupes = dedupe.filter_new(candidates, existing)

        new_urls = {c.source_url for c in new}
        assert new_urls == {
            "https://example.com/articles/ai-soc-triage",
            "https://example.com/articles/llm-phishing",
        }
        assert len(dupes) == 1
        assert dupes[0].source_url == "https://www.example.com/articles/existing-story/"
