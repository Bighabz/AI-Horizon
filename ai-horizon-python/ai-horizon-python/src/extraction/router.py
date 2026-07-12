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


def _transcribe_via_gemini(video_id: str) -> str | None:
    """
    Last-resort ASR: Gemini ingests public YouTube URLs natively and can transcribe
    the audio even when the video has no caption track. The result is AI-generated
    text, not the official captions. Disable with YT_GEMINI_FALLBACK=0.

    Takes the bare video id and builds the canonical watch URL: Gemini only
    recognizes clean YouTube URLs — playlist/radio params make it fetch the
    page as a generic file and fail with 'Unsupported MIME type: text/html'.
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
                types.Part(
                    file_data=types.FileData(
                        file_uri=f"https://www.youtube.com/watch?v={video_id}"
                    ),
                    # Cap the window: >3h of frames trips Gemini's 10,800-image
                    # limit, and classification only ever sees the first 30k
                    # chars anyway. Oversized end_offset is fine on short videos.
                    video_metadata=types.VideoMetadata(
                        fps=0.1, start_offset="0s", end_offset="1800s"
                    ),
                ),
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
    3. Gemini video understanding (ASR - works even without captions)

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

    # Tier 3: Gemini ASR - the only tier that works on caption-less videos
    text = _transcribe_via_gemini(video_id)
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
    """Extract text content from a web page with trafilatura."""
    import trafilatura

    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded)
            if text and len(text) > 100:  # Ensure we got meaningful content
                return text
    except Exception as e:
        logger.warning(f"Trafilatura failed for {url}: {e}")

    raise ValueError(f"Could not extract content from URL: {url}. Try submitting the text directly.")
