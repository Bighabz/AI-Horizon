"""Main classification logic using Gemini."""

import json
import logging
from typing import Optional

from google import genai
from google.genai import types

from src.config import get_settings
from src.classification.models import (
    Artifact,
    ClassificationResult,
    ClassificationType,
    DCWFTaskMapping,
    Scores,
)
from src.classification.prompts import CLASSIFICATION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class HorizonClassifier:
    """Classifies artifacts according to AI impact on DCWF tasks."""

    def __init__(self, dcwf_store_name: Optional[str] = None):
        """
        Initialize the classifier.
        
        Args:
            dcwf_store_name: Gemini File Search store containing DCWF reference data.
                             If None, uses value from settings.
        """
        settings = get_settings()
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_model
        self.dcwf_store_name = dcwf_store_name or settings.dcwf_store_name

    def classify(self, artifact: Artifact) -> ClassificationResult:
        """
        Classify an artifact according to AI impact on cybersecurity workforce.
        
        Args:
            artifact: The artifact to classify.
            
        Returns:
            ClassificationResult with category, scores, and DCWF mappings.
        """
        logger.info(f"Classifying artifact: {artifact.artifact_id}")
        
        # Build the prompt
        user_prompt = self._build_classification_prompt(artifact)
        
        # Configure tools (include DCWF File Search if available)
        tools = []
        if self.dcwf_store_name:
            tools.append(
                types.Tool(
                    file_search=types.FileSearch(
                        file_search_store_names=[self.dcwf_store_name]
                    )
                )
            )
        
        # Generate classification
        config = types.GenerateContentConfig(
            system_instruction=CLASSIFICATION_SYSTEM_PROMPT,
            response_mime_type="application/json",
        )
        
        if tools:
            config.tools = tools
        
        response = self.client.models.generate_content(
            model=self.model,
            contents=user_prompt,
            config=config,
        )
        
        # Parse response
        result = self._parse_classification_response(response.text)
        logger.info(f"Classification complete: {result.classification} ({result.confidence:.2f})")
        
        return result

    def _build_classification_prompt(self, artifact: Artifact) -> str:
        """Build the classification prompt for an artifact."""
        prompt = f"""
Analyze the following artifact and classify its impact on the cybersecurity workforce.

## Artifact Information

**Title**: {artifact.title}
**Source Type**: {artifact.source_type.value}
**Source URL**: {artifact.source_url or 'N/A'}
**Retrieved**: {artifact.retrieved_on.isoformat()}

## Content

{artifact.content[:50000]}  # Limit content length

---

Provide your classification as JSON following the schema specified in your instructions.
Use the DCWF reference data to identify relevant tasks and work roles.
"""
        return prompt

    def _parse_classification_response(self, response_text: str) -> ClassificationResult:
        """Parse the JSON response into a ClassificationResult."""
        try:
            # Clean up response if needed
            text = response_text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            
            data = json.loads(text.strip())
            
            # Parse DCWF task mappings
            dcwf_tasks = []
            for task_data in data.get("dcwf_tasks", []):
                dcwf_tasks.append(DCWFTaskMapping(
                    task_id=task_data["task_id"],
                    relevance_score=task_data.get("relevance_score", 0.5),
                    impact_description=task_data.get("impact_description", ""),
                ))
            
            # Parse scores
            scores_data = data.get("scores", {})
            scores = Scores(
                credibility=scores_data.get("credibility", 0.5),
                impact=scores_data.get("impact", 0.5),
                specificity=scores_data.get("specificity", 0.5),
            )
            
            # Map classification string to enum
            classification_str = data.get("classification", "Augment")
            classification = ClassificationType(classification_str)
            
            return ClassificationResult(
                classification=classification,
                confidence=data.get("confidence", 0.5),
                rationale=data.get("rationale", ""),
                scores=scores,
                dcwf_tasks=dcwf_tasks,
                work_roles=data.get("work_roles", []),
                key_findings=data.get("key_findings", []),
            )
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse classification response: {e}")
            logger.debug(f"Raw response: {response_text}")
            
            # Return a default result on parse failure
            return ClassificationResult(
                classification=ClassificationType.AUGMENT,
                confidence=0.3,
                rationale="Classification parsing failed - manual review required",
                scores=Scores(credibility=0.5, impact=0.5, specificity=0.5),
                dcwf_tasks=[],
                work_roles=[],
                key_findings=["Parse error - review raw content"],
            )

    def classify_batch(self, artifacts: list[Artifact]) -> list[ClassificationResult]:
        """
        Classify multiple artifacts.
        
        Args:
            artifacts: List of artifacts to classify.
            
        Returns:
            List of classification results in the same order.
        """
        results = []
        for i, artifact in enumerate(artifacts):
            logger.info(f"Processing artifact {i+1}/{len(artifacts)}")
            result = self.classify(artifact)
            results.append(result)
        return results
