"""Smoke test: the FastAPI app must import cleanly without real credentials.

Database access is stubbed out before import so no connection is attempted;
env placeholders come from conftest.py. No Gemini calls happen at import time
(the client object is constructed lazily and never used here).
"""

import importlib
import sys


def test_fastapi_app_imports_with_fake_env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-test-key-not-a-real-secret")
    monkeypatch.setenv("ADMIN_API_KEY", "fake-admin-key-for-tests")

    # Stub the DB layer BEFORE importing the app so module-level startup code
    # (init_db + load_evidence_store) never opens a connection.
    import src.api.db as db

    monkeypatch.setattr(db, "init_db", lambda: None)
    monkeypatch.setattr(db, "load_artifacts", lambda: [])

    sys.modules.pop("src.api.main", None)
    main = importlib.import_module("src.api.main")

    assert main.app is not None
    assert main.app.title == "AI Horizon API"

    paths = {getattr(route, "path", None) for route in main.app.routes}
    for expected in ("/api/health", "/api/submit", "/api/chat", "/api/search"):
        assert expected in paths, f"route {expected} missing"


def test_ingestion_dry_run_modules_do_not_import_api(monkeypatch):
    """The dry-run path must stay lightweight: importing the ingestion modules
    must not pull in the FastAPI app (which triggers DB/startup code)."""
    for mod in ("src.api.main",):
        sys.modules.pop(mod, None)

    import src.ingestion.dedupe  # noqa: F401
    import src.ingestion.fetcher  # noqa: F401
    import src.ingestion.normalizer  # noqa: F401
    import src.ingestion.pipeline  # noqa: F401

    assert "src.api.main" not in sys.modules
