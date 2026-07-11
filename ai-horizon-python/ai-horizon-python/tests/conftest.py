"""Shared pytest fixtures for the AI Horizon backend tests.

All tests must run fully offline: no Gemini, no database, no feed fetches.
Placeholder env values below are obviously fake and only exist so imports
that read env vars never require real credentials.
"""

import os
from pathlib import Path

import pytest

# Set BEFORE any src imports happen during collection.
os.environ.setdefault("GEMINI_API_KEY", "fake-test-key-not-a-real-secret")
os.environ.setdefault("ADMIN_API_KEY", "fake-admin-key-for-tests")
os.environ.setdefault("LOG_LEVEL", "WARNING")

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def rss_xml() -> str:
    return (FIXTURES_DIR / "rss_sample.xml").read_text(encoding="utf-8")


@pytest.fixture
def atom_xml() -> str:
    return (FIXTURES_DIR / "atom_sample.xml").read_text(encoding="utf-8")


@pytest.fixture
def evidence_store_path() -> Path:
    return FIXTURES_DIR / "evidence_store_fixture.json"
