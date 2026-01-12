"""
Supabase client for AI Horizon backend.
Replaces JSON file storage with Supabase PostgreSQL.
"""
import os
import logging
from typing import Optional
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase: Optional[Client] = None

def get_supabase() -> Client:
    """Get or create Supabase client."""
    global supabase
    if supabase is None:
        if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        logger.info("Supabase client initialized")
    return supabase


def load_artifacts() -> list[dict]:
    """Load all artifacts from Supabase and transform to expected format."""
    try:
        client = get_supabase()
        response = client.table("document_registry").select("*").order("created_at", desc=True).execute()
        logger.info(f"Loaded {len(response.data)} artifacts from Supabase")

        # Transform Supabase columns to expected app format
        transformed = []
        for row in response.data:
            transformed.append({
                "artifact_id": f"artifact_{row['id'][:12]}" if row.get('id') else None,
                "title": row.get("file_name"),
                "source_url": row.get("source_url"),
                "url": row.get("source_url"),  # Alias
                "source_type": row.get("source_type", "Article"),
                "resource_type": row.get("source_type", "Article"),
                "classification": row.get("classification"),
                "confidence": row.get("confidence"),
                "rationale": row.get("rationale"),
                "dcwf_tasks": row.get("dcwf_tasks", []),
                "key_findings": row.get("key_findings", []),
                "work_role": row.get("dcwf_tasks", [{}])[0].get("work_role") if row.get("dcwf_tasks") else "Cyber Defense Analyst",
                "work_roles": [t.get("work_role") for t in row.get("dcwf_tasks", []) if t.get("work_role")] or ["Cyber Defense Analyst"],
                "difficulty": "Advanced" if row.get("confidence", 0) > 0.7 else "Beginner",
                "is_free": True,
                "stored_at": row.get("created_at"),
                "supabase_id": row.get("id"),  # Keep original ID for deletion
            })

        return transformed
    except Exception as e:
        logger.error(f"Failed to load artifacts from Supabase: {e}")
        return []


def save_artifact(artifact_data: dict) -> bool:
    """Save a single artifact to Supabase."""
    try:
        client = get_supabase()

        # Map our artifact data to document_registry columns
        # Try both 'url' and 'source_url' keys for source URL
        source_url = artifact_data.get("source_url") or artifact_data.get("url") or ""

        record = {
            "file_name": artifact_data.get("title", "Untitled"),
            "source_type": artifact_data.get("source_type") or artifact_data.get("resource_type", "Article"),
            "source_url": source_url,
            "classification": artifact_data.get("classification", "Augment"),
            "confidence": artifact_data.get("confidence", 0.5),
            "rationale": artifact_data.get("rationale", ""),
            "dcwf_tasks": artifact_data.get("dcwf_tasks", []),
            "key_findings": artifact_data.get("key_findings", []),
            "scores": artifact_data.get("scores", {}),
            "content_length": len(artifact_data.get("content", "")),
            "extraction_method": artifact_data.get("extraction_method", "trafilatura"),
        }

        response = client.table("document_registry").insert(record).execute()
        logger.info(f"Saved artifact to Supabase: {record['file_name']} with URL: {source_url[:50] if source_url else 'NONE'}")
        return True
    except Exception as e:
        logger.error(f"Failed to save artifact to Supabase: {e}")
        return False


def search_artifacts(query: str, limit: int = 5) -> list[dict]:
    """Search artifacts in Supabase using text search."""
    try:
        client = get_supabase()

        # Use ilike for basic text search across multiple columns
        response = client.table("document_registry").select("*").or_(
            f"file_name.ilike.%{query}%,rationale.ilike.%{query}%"
        ).limit(limit).execute()

        return response.data
    except Exception as e:
        logger.error(f"Failed to search artifacts in Supabase: {e}")
        return []


def get_stats() -> dict:
    """Get statistics from Supabase."""
    try:
        client = get_supabase()

        # Get all artifacts for stats calculation
        response = client.table("document_registry").select("classification,source_type").execute()
        artifacts = response.data

        # Calculate stats
        classifications = {"replace": 0, "augment": 0, "remain_human": 0, "new_task": 0}
        source_types = {}

        for artifact in artifacts:
            cls = artifact.get("classification", "").lower().replace(" ", "_")
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
        logger.error(f"Failed to get stats from Supabase: {e}")
        return {
            "total_resources": 0,
            "classifications": {"replace": 0, "augment": 0, "remain_human": 0, "new_task": 0},
            "resource_types": {},
        }


def delete_artifact(artifact_id: str) -> bool:
    """Delete an artifact by ID."""
    try:
        client = get_supabase()
        client.table("document_registry").delete().eq("id", artifact_id).execute()
        logger.info(f"Deleted artifact {artifact_id} from Supabase")
        return True
    except Exception as e:
        logger.error(f"Failed to delete artifact from Supabase: {e}")
        return False
