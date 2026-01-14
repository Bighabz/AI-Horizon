"""
Reorganize Gemini File Search stores into Evidence and Resources.

This script:
1. Creates a new RESOURCES store
2. Creates a new EVIDENCE store (replacing old ARTIFACTS store)
3. Migrates all Supabase items to the correct store based on submission_type
"""

import os
import sys
import json
import tempfile
import time
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from google import genai
from supabase import create_client

# Initialize clients
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not all([GEMINI_API_KEY, SUPABASE_URL, SUPABASE_KEY]):
    print("ERROR: Missing required environment variables")
    sys.exit(1)

gemini_client = genai.Client(api_key=GEMINI_API_KEY)
supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)


def create_store(display_name: str) -> str:
    """Create a new File Search store."""
    print(f"Creating store: {display_name}")
    store = gemini_client.file_search_stores.create(
        config={"display_name": display_name}
    )
    print(f"  Created: {store.name}")
    return store.name


def upload_to_store(store_name: str, item: dict) -> bool:
    """Upload a single item to a File Search store."""
    # Create temp JSON file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(item, f, indent=2, default=str)
        temp_path = f.name

    try:
        title = item.get('title', item.get('file_name', 'Untitled'))[:50]
        operation = gemini_client.file_search_stores.upload_to_file_search_store(
            file=temp_path,
            file_search_store_name=store_name,
            config={"display_name": title},
        )

        # Wait for completion
        while not operation.done:
            time.sleep(2)
            operation = gemini_client.operations.get(operation)

        return True
    except Exception as e:
        print(f"    ERROR uploading {title}: {e}")
        return False
    finally:
        os.unlink(temp_path)


def get_all_items():
    """Fetch all items from Supabase."""
    response = supabase_client.table("document_registry").select("*").execute()
    return response.data


def main():
    print("=" * 60)
    print("AI Horizon - Reorganize File Stores")
    print("=" * 60)
    print()

    # Step 1: Create new stores
    print("Step 1: Creating new File Search stores...")
    print("-" * 40)

    evidence_store = create_store("AI Horizon Evidence Store")
    resources_store = create_store("AI Horizon Resources Store")

    print()
    print("New stores created:")
    print(f"  EVIDENCE_STORE_NAME={evidence_store}")
    print(f"  RESOURCES_STORE_NAME={resources_store}")
    print()

    # Step 2: Fetch all items from Supabase
    print("Step 2: Fetching items from Supabase...")
    print("-" * 40)

    items = get_all_items()
    print(f"  Found {len(items)} items in Supabase")

    # Separate by submission_type
    evidence_items = [i for i in items if i.get('submission_type', 'evidence') == 'evidence']
    resource_items = [i for i in items if i.get('submission_type') == 'resource']

    print(f"  Evidence items: {len(evidence_items)}")
    print(f"  Resource items: {len(resource_items)}")
    print()

    # Step 3: Upload evidence items
    print("Step 3: Uploading evidence items...")
    print("-" * 40)

    evidence_success = 0
    for i, item in enumerate(evidence_items, 1):
        title = (item.get('file_name') or 'Untitled')[:40]
        print(f"  [{i}/{len(evidence_items)}] {title}...", end=" ", flush=True)

        if upload_to_store(evidence_store, item):
            print("OK")
            evidence_success += 1
        else:
            print("FAILED")

        # Small delay to avoid rate limits
        time.sleep(0.5)

    print(f"  Uploaded {evidence_success}/{len(evidence_items)} evidence items")
    print()

    # Step 4: Upload resource items
    print("Step 4: Uploading resource items...")
    print("-" * 40)

    resource_success = 0
    for i, item in enumerate(resource_items, 1):
        title = (item.get('file_name') or 'Untitled')[:40]
        print(f"  [{i}/{len(resource_items)}] {title}...", end=" ", flush=True)

        if upload_to_store(resources_store, item):
            print("OK")
            resource_success += 1
        else:
            print("FAILED")

        # Small delay to avoid rate limits
        time.sleep(0.5)

    print(f"  Uploaded {resource_success}/{len(resource_items)} resource items")
    print()

    # Step 5: Summary
    print("=" * 60)
    print("MIGRATION COMPLETE")
    print("=" * 60)
    print()
    print("Update your .env file with these new store names:")
    print()
    print(f"EVIDENCE_STORE_NAME={evidence_store}")
    print(f"RESOURCES_STORE_NAME={resources_store}")
    print()
    print("You can delete the old ARTIFACTS_STORE_NAME line.")
    print()
    print(f"Evidence: {evidence_success}/{len(evidence_items)} uploaded")
    print(f"Resources: {resource_success}/{len(resource_items)} uploaded")


if __name__ == "__main__":
    main()
