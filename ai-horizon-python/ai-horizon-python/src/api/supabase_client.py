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
            # Get work_roles - prefer direct field, fall back to dcwf_tasks extraction
            work_roles = row.get("work_roles") or []
            if not work_roles:
                work_roles = [t.get("work_role") for t in row.get("dcwf_tasks", []) if t.get("work_role")]
            if not work_roles:
                work_roles = ["Cyber Defense Analyst"]  # Default fallback

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
                "work_role": work_roles[0] if work_roles else "Cyber Defense Analyst",
                "work_roles": work_roles,
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

        # Get work_roles - use provided or extract from dcwf_tasks
        work_roles = artifact_data.get("work_roles", [])
        if not work_roles and artifact_data.get("dcwf_tasks"):
            work_roles = [t.get("work_role") for t in artifact_data.get("dcwf_tasks", []) if t.get("work_role")]

        record = {
            "file_name": artifact_data.get("title", "Untitled"),
            "source_type": artifact_data.get("source_type") or artifact_data.get("resource_type", "Article"),
            "source_url": source_url,
            "classification": artifact_data.get("classification", "Augment"),
            "confidence": artifact_data.get("confidence", 0.5),
            "rationale": artifact_data.get("rationale", ""),
            "dcwf_tasks": artifact_data.get("dcwf_tasks", []),
            "key_findings": artifact_data.get("key_findings", []),
            "work_roles": work_roles,  # Save work_roles to database
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


def check_url_duplicate(url: str) -> dict | None:
    """Check if a URL already exists in Supabase. Returns the existing record if found."""
    if not url:
        return None

    try:
        client = get_supabase()

        # Normalize URL for comparison (remove trailing slashes, www, etc.)
        normalized = url.strip().rstrip('/').lower()
        if normalized.startswith('https://www.'):
            normalized = normalized.replace('https://www.', 'https://')
        elif normalized.startswith('http://www.'):
            normalized = normalized.replace('http://www.', 'http://')

        # Check for exact match first
        response = client.table("document_registry").select("*").eq("source_url", url).limit(1).execute()
        if response.data:
            logger.info(f"Found duplicate URL in Supabase: {url}")
            return response.data[0]

        # Also check normalized version
        response = client.table("document_registry").select("*").ilike("source_url", f"%{normalized.split('://')[-1]}%").limit(1).execute()
        if response.data:
            # Verify it's actually a match (not just contains)
            stored_url = response.data[0].get("source_url", "").strip().rstrip('/').lower()
            if stored_url.startswith('https://www.'):
                stored_url = stored_url.replace('https://www.', 'https://')
            elif stored_url.startswith('http://www.'):
                stored_url = stored_url.replace('http://www.', 'http://')

            if normalized == stored_url or normalized.split('://')[-1] == stored_url.split('://')[-1]:
                logger.info(f"Found duplicate URL (normalized) in Supabase: {url}")
                return response.data[0]

        return None
    except Exception as e:
        logger.error(f"Failed to check URL duplicate in Supabase: {e}")
        return None


def get_all_source_urls() -> set:
    """Get all source URLs from Supabase for deduplication."""
    try:
        client = get_supabase()
        response = client.table("document_registry").select("source_url").execute()
        urls = set()
        for row in response.data:
            url = row.get("source_url")
            if url:
                urls.add(url.strip().rstrip('/').lower())
        logger.info(f"Loaded {len(urls)} URLs from Supabase for deduplication")
        return urls
    except Exception as e:
        logger.error(f"Failed to load URLs from Supabase: {e}")
        return set()
