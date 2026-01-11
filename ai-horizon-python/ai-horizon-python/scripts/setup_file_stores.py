#!/usr/bin/env python3
"""Set up Gemini File Search stores for AI Horizon."""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from google import genai

load_dotenv()


def main():
    """Create File Search stores for AI Horizon."""
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("Error: GEMINI_API_KEY not set in environment")
        print("Please add your API key to .env file")
        sys.exit(1)
    
    print("Initializing Gemini client...")
    client = genai.Client(api_key=api_key)
    
    # Create DCWF reference store
    print("\nCreating DCWF reference store...")
    dcwf_store = client.file_search_stores.create(
        config={"display_name": "ai-horizon-dcwf-reference"}
    )
    print(f"[OK] Created: {dcwf_store.name}")
    
    # Create artifacts store
    print("\nCreating artifacts store...")
    artifacts_store = client.file_search_stores.create(
        config={"display_name": "ai-horizon-classified-artifacts"}
    )
    print(f"[OK] Created: {artifacts_store.name}")
    
    # Output for .env
    print("\n" + "="*60)
    print("Add these to your .env file:")
    print("="*60)
    print(f"DCWF_STORE_NAME={dcwf_store.name}")
    print(f"ARTIFACTS_STORE_NAME={artifacts_store.name}")
    print("="*60)
    
    # Optionally update .env
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        response = input("\nWould you like to update .env automatically? (y/n): ")
        if response.lower() == "y":
            with open(env_path, "a") as f:
                f.write(f"\n# File Search Stores (added by setup script)\n")
                f.write(f"DCWF_STORE_NAME={dcwf_store.name}\n")
                f.write(f"ARTIFACTS_STORE_NAME={artifacts_store.name}\n")
            print("[OK] Updated .env file")
    
    print("\nSetup complete! Next steps:")
    print("1. Import DCWF data: python scripts/import_dcwf.py --file data/dcwf/dcwf_tasks.json")
    print("2. Start classifying: python -m src.main classify --file your_document.pdf")
    print("3. Chat with the agent: python -m src.main chat")


if __name__ == "__main__":
    main()
