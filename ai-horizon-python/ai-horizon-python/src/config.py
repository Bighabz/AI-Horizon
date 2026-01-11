"""Configuration management for AI Horizon."""

import os
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Gemini API
    gemini_api_key: str = Field(..., env="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash", env="GEMINI_MODEL")
    
    # File Search Stores
    dcwf_store_name: Optional[str] = Field(default=None, env="DCWF_STORE_NAME")
    artifacts_store_name: Optional[str] = Field(default=None, env="ARTIFACTS_STORE_NAME")
    
    # Paths
    project_root: Path = Field(default_factory=lambda: Path(__file__).parent.parent)
    data_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent / "data")
    dcwf_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent / "data" / "dcwf")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Classification
    default_confidence_threshold: float = Field(default=0.7)
    max_dcwf_tasks_per_artifact: int = Field(default=10)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings
