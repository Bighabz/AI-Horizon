"""Content extraction routing based on file type."""

import logging
import os
import re
from pathlib import Path

logger = logging.getLogger(__name__)


class NoCaptionsError(Exception):
    """The video verifiably has no captions and no ASR fallback produced a transcript."""


class TranscriptFetchError(Exception):
    """Every transcript source failed for transient reasons (IP block, outage, credits)."""


def extract_content(source: Path | str) -> str:
    """
    Extract text content from various sources.

    Args:
        source: File path or URL to extract from.

    Returns:
        Extracted text content.
    """
    if isinstance(source, str):
        source = Path(source)

    if not source.exists():
        raise FileNotFoundError(f"File not found: {source}")

    ext = source.suffix.lower()

    if ext == ".pdf":
        return extract_pdf(source)
    elif ext in (".docx", ".doc"):
        return extract_docx(source)
    elif ext in (".txt", ".md", ".json"):
        return extract_text(source)
    else:
        logger.warning(f"Unknown file type: {ext}, treating as text")
        return extract_text(source)


def extract_pdf(file_path: Path) -> str:
    """Extract text from a PDF file."""
    try:
        import pdfplumber

        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)

        return "\n\n".join(text_parts)

    except ImportError:
        # Fallback to PyPDF2
        from PyPDF2 import PdfReader

        reader = PdfReader(file_path)
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)

        return "\n\n".join(text_parts)


def extract_docx(file_path: Path) -> str:
    """Extract text from a DOCX file."""
    from docx import Document

    doc = Document(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def extract_text(file_path: Path) -> str:
    """Extract text from a plain text file."""
    return file_path.read_text(encoding="utf-8")


def _youtube_video_id(url: str) -> str:
    """Extract the video ID from a YouTube URL."""
    patterns = [
        r"(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)",
        r"youtube\.com\/embed\/([^&\n?#]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Could not extract video ID from URL: {url}")


def _proxy_config():
    """Optional proxy for youtube-transcript-api, from env. None if unconfigured."""
    from youtube_transcript_api.proxies import GenericProxyConfig, WebshareProxyConfig

    ws_user = os.getenv("WEBSHARE_PROXY_USERNAME")
    ws_pass = os.getenv("WEBSHARE_PROXY_PASSWORD")
    if ws_user and ws_pass:
        return WebshareProxyConfig(proxy_username=ws_user, proxy_password=ws_pass)
    proxy_url = os.getenv("YT_PROXY_URL")
    if proxy_url:
        return GenericProxyConfig(http_url=proxy_url, https_url=proxy_url)
    return None


def _fetch_captions(video_id: str, proxy_config=None) -> str:
    """Fetch the official caption track via youtube-transcript-api (v1.x API)."""
    from youtube_transcript_api import YouTubeTranscriptApi

    api = YouTubeTranscriptApi(proxy_config=proxy_config) if proxy_config else YouTubeTranscriptApi()
    transcript = api.fetch(video_id)
    return " ".join(entry.text for entry in transcript)


def _fetch_via_dumpling(url: str) -> str | None:
    """
    Dumpling.ai transcript endpoint — runs from Dumpling's infrastructure, so it
    works even when YouTube blocks our own egress IP. Returns None when
    unconfigured or transiently failing; raises NoCaptionsError on Dumpling's 404
    (their confirmation that the video has no caption track).
    """
    import requests

    api_key = os.getenv("DUMPLING_API_KEY")
    if not api_key:
        return None
    try:
        response = requests.post(
            "https://app.dumplingai.com/api/v1/get-youtube-transcript",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={"videoUrl": url, "includeTimestamps": False, "preferredLanguage": "en"},
            timeout=60,
        )
    except Exception as e:
        logger.warning(f"Dumpling.ai transcript request failed: {e}")
        return None

    if response.status_code == 200:
        text = (response.json().get("transcript") or "").strip()
        return text or None
    if response.status_code == 404:
        raise NoCaptionsError(f"No captions found for video: {url}")
    if response.status_code == 402:
        logger.warning("Dumpling.ai account is out of credits - transcript fallback skipped")
        return None
    logger.warning(f"Dumpling.ai transcript returned {response.status_code}: {response.text[:200]}")
    return None


def _transcribe_via_gemini(url: str) -> str | None:
    """
    Last-resort ASR: Gemini ingests public YouTube URLs natively and can transcribe
    the audio even when the video has no caption track. The result is AI-generated
    text, not the official captions. Disable with YT_GEMINI_FALLBACK=0.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or os.getenv("YT_GEMINI_FALLBACK", "1").lower() in ("0", "false", "off"):
        return None
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            contents=types.Content(parts=[
                types.Part(file_data=types.FileData(file_uri=url)),
                types.Part(text=(
                    "Transcribe the spoken audio of this video verbatim as plain text. "
                    "No timestamps, speaker labels, or commentary."
                )),
            ]),
        )
        text = (response.text or "").strip()
        # Guard against refusals / empty transcriptions masquerading as success
        return text if len(text) >= 40 else None
    except Exception as e:
        logger.warning(f"Gemini video transcription failed: {e}")
        return None


def extract_youtube(url: str) -> str:
    """
    Extract a transcript for a YouTube video via a layered fallback chain:

    1. youtube-transcript-api direct (free; YouTube blocks most datacenter IPs)
    2. youtube-transcript-api through a proxy, if one is configured in env
    3. Dumpling.ai's transcript endpoint (their egress IP, our credits)
    4. Gemini video understanding (ASR - works even without captions)

    Raises NoCaptionsError when the video verifiably has no captions and ASR is
    unavailable, TranscriptFetchError when every source failed transiently, and
    ValueError for bad URLs or unavailable videos.
    """
    from youtube_transcript_api import (
        CouldNotRetrieveTranscript,
        NoTranscriptFound,
        RequestBlocked,
        TranscriptsDisabled,
        VideoUnavailable,
    )

    video_id = _youtube_video_id(url)
    no_captions = False

    # Tiers 1-2: official caption track, direct then (if configured) via proxy
    proxy = _proxy_config()
    for proxy_config in ([None, proxy] if proxy else [None]):
        via = "proxy" if proxy_config else "direct"
        try:
            transcript = _fetch_captions(video_id, proxy_config)
            logger.info(f"YouTube transcript via {via} fetch: {len(transcript)} chars")
            return transcript
        except (TranscriptsDisabled, NoTranscriptFound):
            # Genuinely no caption track: scraping more won't help, but ASR might
            no_captions = True
            break
        except VideoUnavailable as e:
            raise ValueError(
                f"YouTube video is unavailable (deleted, private, or region-locked): {url}"
            ) from e
        except RequestBlocked as e:
            logger.warning(f"YouTube blocked the {via} transcript request: {e}")
        except CouldNotRetrieveTranscript as e:
            logger.warning(f"Transcript {via} fetch failed: {e}")
        except Exception as e:
            logger.warning(f"Unexpected transcript error on {via} fetch: {e}")

    # Tier 3: Dumpling (pointless if we already know there are no captions to scrape)
    if not no_captions:
        try:
            text = _fetch_via_dumpling(url)
            if text:
                logger.info(f"YouTube transcript via Dumpling.ai: {len(text)} chars")
                return text
        except NoCaptionsError:
            no_captions = True

    # Tier 4: Gemini ASR - the only tier that works on caption-less videos
    text = _transcribe_via_gemini(url)
    if text:
        logger.info(
            f"YouTube transcript via Gemini ASR: {len(text)} chars (AI-generated, not official captions)"
        )
        return text

    if no_captions:
        raise NoCaptionsError(
            f"Video has no captions and audio transcription is unavailable: {url}"
        )
    raise TranscriptFetchError(
        f"All transcript sources failed for {url} - likely temporary (IP block or service outage)"
    )


def extract_web(url: str) -> str:
    """
    Extract text content from a web page.

    Tries trafilatura first (free, local), falls back to Dumpling.ai if blocked.
    """
    import trafilatura
    import requests

    # Try trafilatura first (free, local)
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded)
            if text and len(text) > 100:  # Ensure we got meaningful content
                return text
    except Exception as e:
        logger.warning(f"Trafilatura failed for {url}: {e}")

    # Fallback to Dumpling.ai if configured
    dumpling_key = os.getenv("DUMPLING_API_KEY")
    if dumpling_key:
        try:
            logger.info(f"Trying Dumpling.ai for {url}")
            response = requests.post(
                "https://app.dumplingai.com/api/v1/scrape",
                headers={
                    "Authorization": f"Bearer {dumpling_key}",
                    "Content-Type": "application/json"
                },
                json={"url": url},
                timeout=60
            )
            if response.status_code == 200:
                data = response.json()
                text = data.get("content") or data.get("text") or data.get("article", {}).get("content")
                if text:
                    return text
            if response.status_code == 402:
                logger.warning("Dumpling.ai account is out of credits - web fallback skipped")
            else:
                logger.warning(f"Dumpling.ai returned {response.status_code}: {response.text[:200]}")
        except Exception as e:
            logger.error(f"Dumpling.ai failed: {e}")

    raise ValueError(f"Could not extract content from URL: {url}. Try submitting the text directly.")
