"""
PostgreSQL database client for AI Horizon backend.
Uses psycopg2 with Railway PostgreSQL (replaces Supabase client).
"""
import json
import logging
import os
from contextlib import contextmanager
from typing import Optional

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS document_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_name TEXT,
    source_url TEXT,
    source_type TEXT DEFAULT 'Article',
    classification TEXT,
    confidence FLOAT,
    rationale TEXT,
    dcwf_tasks JSONB DEFAULT '[]'::jsonb,
    key_findings JSONB DEFAULT '[]'::jsonb,
    work_roles JSONB DEFAULT '[]'::jsonb,
    submission_type TEXT DEFAULT 'evidence',
    scores JSONB DEFAULT '{}'::jsonb,
    content_length INTEGER DEFAULT 0,
    extraction_method TEXT DEFAULT 'trafilatura',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
"""


@contextmanager
def get_db():
    """Get a database connection (context manager)."""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL must be set in environment")
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create tables if they don't exist."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLE_SQL)
    logger.info("Database tables initialized")


def load_artifacts() -> list[dict]:
    """Load all artifacts and transform to expected app format."""
    try:
        with get_db() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM document_registry ORDER BY created_at DESC")
                rows = cur.fetchall()

        logger.info(f"Loaded {len(rows)} artifacts from PostgreSQL")

        transformed = []
        for row in rows:
            work_roles = row.get("work_roles") or []
            if not work_roles:
                work_roles = [t.get("work_role") for t in (row.get("dcwf_tasks") or []) if t.get("work_role")]
            if not work_roles:
                work_roles = ["Cyber Defense Analyst"]

            row_id = str(row["id"])
            transformed.append({
                "artifact_id": f"artifact_{row_id[:12]}",
                "title": row.get("file_name"),
                "source_url": row.get("source_url"),
                "url": row.get("source_url"),
                "source_type": row.get("source_type", "Article"),
                "resource_type": row.get("source_type", "Article"),
                "classification": row.get("classification"),
                "confidence": row.get("confidence"),
                "rationale": row.get("rationale"),
                "dcwf_tasks": row.get("dcwf_tasks") or [],
                "key_findings": row.get("key_findings") or [],
                "work_role": work_roles[0] if work_roles else "Cyber Defense Analyst",
                "work_roles": work_roles,
                "submission_type": row.get("submission_type", "evidence"),
                "difficulty": "Advanced" if (row.get("confidence") or 0) > 0.7 else "Beginner",
                "is_free": True,
                "stored_at": row.get("created_at").isoformat() if row.get("created_at") else None,
                "supabase_id": row_id,
            })

        return transformed
    except Exception as e:
        logger.error(f"Failed to load artifacts from PostgreSQL: {e}")
        return []


def save_artifact(artifact_data: dict) -> bool:
    """Save a single artifact."""
    try:
        source_url = artifact_data.get("source_url") or artifact_data.get("url") or ""

        work_roles = artifact_data.get("work_roles", [])
        if not work_roles and artifact_data.get("dcwf_tasks"):
            work_roles = [t.get("work_role") for t in artifact_data.get("dcwf_tasks", []) if t.get("work_role")]

        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO document_registry
                    (file_name, source_type, source_url, classification, confidence,
                     rationale, dcwf_tasks, key_findings, work_roles, submission_type,
                     scores, content_length, extraction_method)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    artifact_data.get("title", "Untitled"),
                    artifact_data.get("source_type") or artifact_data.get("resource_type", "Article"),
                    source_url,
                    artifact_data.get("classification", "Augment"),
                    artifact_data.get("confidence", 0.5),
                    artifact_data.get("rationale", ""),
                    json.dumps(artifact_data.get("dcwf_tasks", [])),
                    json.dumps(artifact_data.get("key_findings", [])),
                    json.dumps(work_roles),
                    artifact_data.get("submission_type", "evidence"),
                    json.dumps(artifact_data.get("scores", {})),
                    len(artifact_data.get("content", "")),
                    artifact_data.get("extraction_method", "trafilatura"),
                ))

        logger.info(f"Saved artifact: {artifact_data.get('title', 'Untitled')} URL: {source_url[:50] if source_url else 'NONE'}")
        return True
    except Exception as e:
        logger.error(f"Failed to save artifact: {e}")
        return False


def search_artifacts(query: str, limit: int = 5) -> list[dict]:
    """Search artifacts using ILIKE text search."""
    try:
        with get_db() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM document_registry
                    WHERE file_name ILIKE %s OR rationale ILIKE %s
                    LIMIT %s
                """, (f"%{query}%", f"%{query}%", limit))
                rows = cur.fetchall()

        results = []
        for row in rows:
            d = dict(row)
            d["id"] = str(d["id"])
            if d.get("created_at"):
                d["created_at"] = d["created_at"].isoformat()
            results.append(d)
        return results
    except Exception as e:
        logger.error(f"Failed to search artifacts: {e}")
        return []


def get_stats() -> dict:
    """Get classification and source type statistics."""
    try:
        with get_db() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT classification, source_type FROM document_registry")
                artifacts = cur.fetchall()

        classifications = {"replace": 0, "augment": 0, "remain_human": 0, "new_task": 0}
        source_types = {}

        for artifact in artifacts:
            cls = (artifact.get("classification") or "").lower().replace(" ", "_")
            if cls in classifications:
                classifications[cls] += 1

            src = artifact.get("source_type", "Unknown")
            source_types[src] = source_types.get(src, 0) + 1

        return {
            "total_resources": len(artifacts),
            "classifications": classifications,
            "resource_types": source_types,
        }
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        return {
            "total_resources": 0,
            "classifications": {"replace": 0, "augment": 0, "remain_human": 0, "new_task": 0},
            "resource_types": {},
        }


def delete_artifact(artifact_id: str) -> bool:
    """Delete an artifact by UUID."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM document_registry WHERE id = %s", (artifact_id,))
        logger.info(f"Deleted artifact {artifact_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete artifact: {e}")
        return False


def check_url_duplicate(url: str) -> dict | None:
    """Check if a URL already exists. Returns the existing record if found."""
    if not url:
        return None

    try:
        normalized = url.strip().rstrip('/').lower()
        if normalized.startswith('https://www.'):
            normalized = normalized.replace('https://www.', 'https://')
        elif normalized.startswith('http://www.'):
            normalized = normalized.replace('http://www.', 'http://')

        with get_db() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # Exact match first
                cur.execute("SELECT * FROM document_registry WHERE source_url = %s LIMIT 1", (url,))
                row = cur.fetchone()
                if row:
                    logger.info(f"Found duplicate URL: {url}")
                    d = dict(row)
                    d["id"] = str(d["id"])
                    return d

                # Normalized match
                url_path = normalized.split('://')[-1]
                cur.execute("SELECT * FROM document_registry WHERE source_url ILIKE %s LIMIT 1", (f"%{url_path}%",))
                row = cur.fetchone()
                if row:
                    stored_url = (row.get("source_url") or "").strip().rstrip('/').lower()
                    if stored_url.startswith('https://www.'):
                        stored_url = stored_url.replace('https://www.', 'https://')
                    elif stored_url.startswith('http://www.'):
                        stored_url = stored_url.replace('http://www.', 'http://')

                    if normalized == stored_url or normalized.split('://')[-1] == stored_url.split('://')[-1]:
                        logger.info(f"Found duplicate URL (normalized): {url}")
                        d = dict(row)
                        d["id"] = str(d["id"])
                        return d

        return None
    except Exception as e:
        logger.error(f"Failed to check URL duplicate: {e}")
        return None


def get_all_source_urls() -> set:
    """Get all source URLs for deduplication."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT source_url FROM document_registry")
                rows = cur.fetchall()

        urls = set()
        for row in rows:
            url = row[0]
            if url:
                urls.add(url.strip().rstrip('/').lower())
        logger.info(f"Loaded {len(urls)} URLs for deduplication")
        return urls
    except Exception as e:
        logger.error(f"Failed to load URLs: {e}")
        return set()
