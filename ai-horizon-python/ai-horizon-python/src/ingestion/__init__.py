"""Feed ingestion pipeline for AI Horizon.

Pulls articles from configured RSS/Atom feeds (see feeds.json), normalizes them
into the same artifact/evidence shape used by the rest of the pipeline, dedupes
against the existing evidence store by URL, and (optionally) routes new items
into the existing Gemini classification + storage entry points.

Usage:
    python -m src.ingestion.run --dry-run            # preview only, no Gemini, no DB writes
    python -m src.ingestion.run --dry-run --limit 5  # cap new items processed
    python -m src.ingestion.run                      # real ingestion (requires Gemini + DB)
"""
