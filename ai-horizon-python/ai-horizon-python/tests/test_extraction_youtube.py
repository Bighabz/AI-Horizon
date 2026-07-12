"""Offline tests for the layered YouTube transcript fallback chain.

The chain (src/extraction/router.py::extract_youtube):
  1. youtube-transcript-api direct
  2. youtube-transcript-api via proxy (only if configured in env)
  3. Gemini video ASR

Tier functions are monkeypatched, so no network is touched. The real
youtube-transcript-api package supplies the exception types the chain
dispatches on, keeping the tests honest about the library contract.
"""

import pytest
from youtube_transcript_api import (
    NoTranscriptFound,
    RequestBlocked,
    TranscriptsDisabled,
    VideoUnavailable,
)

from src.extraction import router
from src.extraction.router import NoCaptionsError, TranscriptFetchError, extract_youtube

URL = "https://www.youtube.com/watch?v=abc123xyz00"


@pytest.fixture(autouse=True)
def no_proxy_no_gemini(monkeypatch):
    """Default: no proxy configured, Gemini fallback disabled."""
    for var in ("WEBSHARE_PROXY_USERNAME", "WEBSHARE_PROXY_PASSWORD", "YT_PROXY_URL"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("YT_GEMINI_FALLBACK", "0")


def test_video_id_parsing():
    assert router._youtube_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert router._youtube_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert router._youtube_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    with pytest.raises(ValueError):
        router._youtube_video_id("https://www.youtube.com/playlist?list=PL123")


def test_direct_fetch_success(monkeypatch):
    monkeypatch.setattr(router, "_fetch_captions", lambda vid, proxy_config=None: "official captions")
    assert extract_youtube(URL) == "official captions"


def test_no_captions_without_gemini_raises_no_captions(monkeypatch):
    def raise_disabled(vid, proxy_config=None):
        raise TranscriptsDisabled(vid)

    monkeypatch.setattr(router, "_fetch_captions", raise_disabled)
    with pytest.raises(NoCaptionsError):
        extract_youtube(URL)


def test_no_captions_but_gemini_asr_still_tries(monkeypatch):
    def raise_disabled(vid, proxy_config=None):
        raise TranscriptsDisabled(vid)

    monkeypatch.setattr(router, "_fetch_captions", raise_disabled)
    monkeypatch.setattr(router, "_transcribe_via_gemini", lambda url: "asr text from captionless video")
    assert extract_youtube(URL) == "asr text from captionless video"


def test_no_transcript_found_also_terminal(monkeypatch):
    def raise_not_found(vid, proxy_config=None):
        raise NoTranscriptFound(vid, ["en"], None)

    monkeypatch.setattr(router, "_fetch_captions", raise_not_found)
    with pytest.raises(NoCaptionsError):
        extract_youtube(URL)


def test_video_unavailable_raises_value_error(monkeypatch):
    def raise_unavailable(vid, proxy_config=None):
        raise VideoUnavailable(vid)

    monkeypatch.setattr(router, "_fetch_captions", raise_unavailable)
    with pytest.raises(ValueError):
        extract_youtube(URL)


def test_ip_block_falls_back_to_gemini(monkeypatch):
    def raise_blocked(vid, proxy_config=None):
        raise RequestBlocked(vid)

    monkeypatch.setattr(router, "_fetch_captions", raise_blocked)
    monkeypatch.setattr(router, "_transcribe_via_gemini", lambda url: "gemini asr transcript")
    assert extract_youtube(URL) == "gemini asr transcript"


def test_all_tiers_fail_raises_transient_error(monkeypatch):
    def raise_blocked(vid, proxy_config=None):
        raise RequestBlocked(vid)

    monkeypatch.setattr(router, "_fetch_captions", raise_blocked)
    monkeypatch.setattr(router, "_transcribe_via_gemini", lambda url: None)
    with pytest.raises(TranscriptFetchError):
        extract_youtube(URL)


def test_proxy_tier_retries_after_block(monkeypatch):
    monkeypatch.setenv("YT_PROXY_URL", "http://user:pass@proxy.test:8080")
    calls = []

    class FakeProxyConfig:
        pass

    def fake_fetch(vid, proxy_config=None):
        calls.append(proxy_config)
        if proxy_config is None:
            raise RequestBlocked(vid)
        return "captions via proxy"

    monkeypatch.setattr(router, "_proxy_config", lambda: FakeProxyConfig())
    monkeypatch.setattr(router, "_fetch_captions", fake_fetch)
    assert extract_youtube(URL) == "captions via proxy"
    assert calls[0] is None and calls[1] is not None


def test_unexpected_error_still_reaches_gemini(monkeypatch):
    def raise_weird(vid, proxy_config=None):
        raise RuntimeError("api surface changed under us")

    monkeypatch.setattr(router, "_fetch_captions", raise_weird)
    monkeypatch.setattr(router, "_transcribe_via_gemini", lambda url: "gemini saves the day")
    assert extract_youtube(URL) == "gemini saves the day"


def test_gemini_fallback_respects_disable_flag(monkeypatch):
    monkeypatch.setenv("YT_GEMINI_FALLBACK", "0")
    assert router._transcribe_via_gemini(URL) is None
