"""Content extraction routing based on file type."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


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


def extract_youtube(url: str) -> str:
    """Extract transcript from a YouTube video."""
    from youtube_transcript_api import YouTubeTranscriptApi
    import re

    # Extract video ID from URL
    patterns = [
        r"(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)",
        r"youtube\.com\/embed\/([^&\n?#]+)",
    ]

    video_id = None
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            break

    if not video_id:
        raise ValueError(f"Could not extract video ID from URL: {url}")

    # Get transcript (API v1.x uses fetch() method)
    ytt_api = YouTubeTranscriptApi()
    transcript = ytt_api.fetch(video_id)

    # Combine transcript parts
    return " ".join([entry.text for entry in transcript])


def extract_web(url: str) -> str:
    """
    Extract text content from a web page.

    Tries trafilatura first (free, local), falls back to Dumpling.ai if blocked.
    """
    import os
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
                "https://api.dumpling.ai/api/v1/extract-article",
                headers={
                    "Authorization": f"Bearer {dumpling_key}",
                    "Content-Type": "application/json"
                },
                json={"url": url},
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                text = data.get("content") or data.get("text") or data.get("article", {}).get("content")
                if text:
                    return text
            logger.warning(f"Dumpling.ai returned {response.status_code}: {response.text[:200]}")
        except Exception as e:
            logger.error(f"Dumpling.ai failed: {e}")

    raise ValueError(f"Could not extract content from URL: {url}. Try submitting the text directly.")
