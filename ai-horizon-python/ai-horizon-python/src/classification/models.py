"""Data models for AI Horizon classification system."""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ClassificationType(str, Enum):
    """Classification categories for AI impact on DCWF tasks."""
    
    REPLACE = "Replace"
    AUGMENT = "Augment"
    REMAIN_HUMAN = "Remain Human"
    NEW_TASK = "New Task"


class SourceType(str, Enum):
    """Types of artifact sources."""
    
    PDF = "pdf"
    DOCX = "docx"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    WEB = "web"
    TEXT = "text"
    UNKNOWN = "unknown"


class Scores(BaseModel):
    """Scoring metrics for classification quality."""
    
    credibility: float = Field(ge=0.0, le=1.0, description="Source reliability score")
    impact: float = Field(ge=0.0, le=1.0, description="Workforce transformation significance")
    specificity: float = Field(ge=0.0, le=1.0, description="DCWF task mapping precision")


class DCWFTaskMapping(BaseModel):
    """Mapping between an artifact and a DCWF task."""
    
    task_id: str = Field(description="DCWF Task ID (e.g., T0597)")
    task_description: Optional[str] = Field(default=None, description="Task description")
    relevance_score: float = Field(ge=0.0, le=1.0, description="How relevant this task is")
    impact_description: str = Field(description="How the artifact impacts this task")


class ClassificationResult(BaseModel):
    """Result of classifying an artifact."""
    
    classification: ClassificationType
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(description="Explanation for the classification")
    scores: Scores
    dcwf_tasks: List[DCWFTaskMapping] = Field(default_factory=list)
    work_roles: List[str] = Field(default_factory=list)
    key_findings: List[str] = Field(default_factory=list)


class Artifact(BaseModel):
    """An artifact (document/evidence) to be classified."""
    
    # Identification
    artifact_id: str = Field(description="Unique identifier")
    title: str = Field(description="Artifact title")
    
    # Content
    content: str = Field(description="Extracted text content")
    summary: Optional[str] = Field(default=None, description="AI-generated summary")
    
    # Source information
    source_url: Optional[str] = Field(default=None, description="Original source URL")
    source_type: SourceType = Field(default=SourceType.UNKNOWN)
    filename: Optional[str] = Field(default=None, description="Original filename")
    
    # Classification (populated after analysis)
    classification: Optional[ClassificationType] = Field(default=None)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    rationale: Optional[str] = Field(default=None)
    
    # Scores
    scores: Optional[Scores] = Field(default=None)
    
    # DCWF Mapping
    dcwf_task_ids: List[str] = Field(default_factory=list)
    work_roles: List[str] = Field(default_factory=list)
    key_findings: List[str] = Field(default_factory=list)
    
    # Metadata
    retrieved_on: datetime = Field(default_factory=datetime.now)
    user_id: Optional[str] = Field(default=None)
    
    def apply_classification(self, result: ClassificationResult) -> None:
        """Apply a classification result to this artifact."""
        self.classification = result.classification
        self.confidence = result.confidence
        self.rationale = result.rationale
        self.scores = result.scores
        self.dcwf_task_ids = [t.task_id for t in result.dcwf_tasks]
        self.work_roles = result.work_roles
        self.key_findings = result.key_findings


class DCWFTask(BaseModel):
    """A DCWF (Defense Cyber Workforce Framework) task."""
    
    task_id: str = Field(description="Unique task identifier (e.g., T0001)")
    nist_sp_id: Optional[str] = Field(default=None, description="NIST SP reference")
    task_name: str = Field(description="Short task name")
    task_description: str = Field(description="Full task description")
    work_role: Optional[str] = Field(default=None, description="Associated work role")
    work_role_id: Optional[str] = Field(default=None, description="Work role identifier")
    competency_area: Optional[str] = Field(default=None, description="Skill category")
    keywords: List[str] = Field(default_factory=list, description="Related keywords")


class ChatMessage(BaseModel):
    """A message in the chat interface."""
    
    role: str = Field(description="user or assistant")
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    citations: List[str] = Field(default_factory=list, description="Source citations")


class QueryResult(BaseModel):
    """Result from a RAG query."""
    
    answer: str
    sources: List[str] = Field(default_factory=list)
    artifacts_referenced: List[str] = Field(default_factory=list)
    dcwf_tasks_mentioned: List[str] = Field(default_factory=list)
