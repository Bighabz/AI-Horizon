"""Gemini File Search integration for RAG storage."""

import json
import logging
import time
from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types

from src.config import get_settings
from src.classification.models import Artifact, DCWFTask

logger = logging.getLogger(__name__)


class FileSearchStore:
    """Wrapper for Gemini File Search operations."""

    def __init__(self):
        """Initialize the File Search client."""
        settings = get_settings()
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.settings = settings

    def create_store(self, display_name: str) -> str:
        """
        Create a new File Search store.
        
        Args:
            display_name: Human-readable name for the store.
            
        Returns:
            The store name (ID) for use in subsequent operations.
        """
        logger.info(f"Creating File Search store: {display_name}")
        
        store = self.client.file_search_stores.create(
            config={"display_name": display_name}
        )
        
        logger.info(f"Created store: {store.name}")
        return store.name

    def upload_file(
        self,
        store_name: str,
        file_path: Path,
        display_name: Optional[str] = None,
        wait_for_completion: bool = True,
    ) -> str:
        """
        Upload a file to a File Search store.
        
        Args:
            store_name: The store to upload to.
            file_path: Path to the file.
            display_name: Optional display name (defaults to filename).
            wait_for_completion: Whether to wait for indexing to complete.
            
        Returns:
            The document name/ID.
        """
        file_path = Path(file_path)
        display_name = display_name or file_path.name
        
        logger.info(f"Uploading {file_path.name} to {store_name}")
        
        operation = self.client.file_search_stores.upload_to_file_search_store(
            file=str(file_path),
            file_search_store_name=store_name,
            config={"display_name": display_name},
        )
        
        if wait_for_completion:
            while not operation.done:
                logger.debug("Waiting for indexing...")
                time.sleep(5)
                operation = self.client.operations.get(operation)
        
        logger.info(f"Upload complete: {display_name}")
        return operation.result.name if operation.result else None

    def upload_artifact(
        self,
        store_name: str,
        artifact: Artifact,
        wait_for_completion: bool = True,
    ) -> str:
        """
        Upload a classified artifact to File Search.
        
        Converts the artifact to a JSON document for storage.
        
        Args:
            store_name: The store to upload to.
            artifact: The artifact to store.
            wait_for_completion: Whether to wait for indexing.
            
        Returns:
            The document name/ID.
        """
        # Create a temporary JSON file
        temp_path = Path(f"/tmp/{artifact.artifact_id}.json")
        
        # Prepare artifact data for storage
        artifact_data = {
            "artifact_id": artifact.artifact_id,
            "title": artifact.title,
            "content": artifact.content,
            "summary": artifact.summary,
            "source_url": artifact.source_url,
            "source_type": artifact.source_type.value,
            "classification": artifact.classification.value if artifact.classification else None,
            "confidence": artifact.confidence,
            "rationale": artifact.rationale,
            "scores": artifact.scores.model_dump() if artifact.scores else None,
            "dcwf_task_ids": artifact.dcwf_task_ids,
            "work_roles": artifact.work_roles,
            "key_findings": artifact.key_findings,
            "retrieved_on": artifact.retrieved_on.isoformat(),
        }
        
        # Write to temp file
        with open(temp_path, "w") as f:
            json.dump(artifact_data, f, indent=2)
        
        try:
            doc_name = self.upload_file(
                store_name=store_name,
                file_path=temp_path,
                display_name=f"{artifact.title} ({artifact.artifact_id})",
                wait_for_completion=wait_for_completion,
            )
            return doc_name
        finally:
            # Clean up temp file
            temp_path.unlink(missing_ok=True)

    def upload_dcwf_tasks(
        self,
        store_name: str,
        tasks: list[DCWFTask],
        batch_size: int = 100,
    ) -> list[str]:
        """
        Upload DCWF tasks to File Search in batches.
        
        Args:
            store_name: The store to upload to.
            tasks: List of DCWF tasks.
            batch_size: Number of tasks per file.
            
        Returns:
            List of document names/IDs.
        """
        logger.info(f"Uploading {len(tasks)} DCWF tasks in batches of {batch_size}")
        
        doc_names = []
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            # Create batch file
            temp_path = Path(f"/tmp/dcwf_batch_{batch_num}.json")
            batch_data = [task.model_dump() for task in batch]
            
            with open(temp_path, "w") as f:
                json.dump(batch_data, f, indent=2)
            
            try:
                doc_name = self.upload_file(
                    store_name=store_name,
                    file_path=temp_path,
                    display_name=f"DCWF Tasks Batch {batch_num}",
                )
                doc_names.append(doc_name)
            finally:
                temp_path.unlink(missing_ok=True)
        
        logger.info(f"Uploaded {len(doc_names)} batch files")
        return doc_names

    def query(
        self,
        store_names: list[str],
        query: str,
        model: str = "gemini-2.5-flash",
    ) -> str:
        """
        Query File Search stores with RAG.
        
        Args:
            store_names: List of store names to search.
            query: The query text.
            model: Gemini model to use.
            
        Returns:
            The generated response.
        """
        logger.debug(f"Querying stores: {store_names}")
        
        response = self.client.models.generate_content(
            model=model,
            contents=query,
            config=types.GenerateContentConfig(
                tools=[
                    types.Tool(
                        file_search=types.FileSearch(
                            file_search_store_names=store_names
                        )
                    )
                ]
            ),
        )
        
        return response.text

    def list_stores(self) -> list[dict]:
        """List all File Search stores."""
        stores = self.client.file_search_stores.list()
        return [{"name": s.name, "display_name": s.display_name} for s in stores]

    def delete_store(self, store_name: str) -> None:
        """Delete a File Search store."""
        logger.info(f"Deleting store: {store_name}")
        self.client.file_search_stores.delete(name=store_name)


class HorizonStorage:
    """High-level storage interface for AI Horizon."""

    def __init__(
        self,
        dcwf_store_name: Optional[str] = None,
        artifacts_store_name: Optional[str] = None,
    ):
        """
        Initialize storage with store names.
        
        Args:
            dcwf_store_name: Store for DCWF reference data.
            artifacts_store_name: Store for classified artifacts.
        """
        settings = get_settings()
        self.file_search = FileSearchStore()
        self.dcwf_store = dcwf_store_name or settings.dcwf_store_name
        self.artifacts_store = artifacts_store_name or settings.artifacts_store_name

    def store_artifact(self, artifact: Artifact) -> str:
        """Store a classified artifact."""
        if not self.artifacts_store:
            raise ValueError("Artifacts store not configured")
        
        return self.file_search.upload_artifact(
            store_name=self.artifacts_store,
            artifact=artifact,
        )

    def query_dcwf(self, query: str) -> str:
        """Query the DCWF reference data."""
        if not self.dcwf_store:
            raise ValueError("DCWF store not configured")
        
        return self.file_search.query(
            store_names=[self.dcwf_store],
            query=query,
        )

    def query_artifacts(self, query: str) -> str:
        """Query classified artifacts."""
        if not self.artifacts_store:
            raise ValueError("Artifacts store not configured")
        
        return self.file_search.query(
            store_names=[self.artifacts_store],
            query=query,
        )

    def query_all(self, query: str) -> str:
        """Query both DCWF and artifacts stores."""
        stores = []
        if self.dcwf_store:
            stores.append(self.dcwf_store)
        if self.artifacts_store:
            stores.append(self.artifacts_store)
        
        if not stores:
            raise ValueError("No stores configured")
        
        return self.file_search.query(
            store_names=stores,
            query=query,
        )
