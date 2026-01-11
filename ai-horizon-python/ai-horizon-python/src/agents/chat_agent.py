"""Conversational RAG agent for AI Horizon."""

import logging
from typing import Optional

from google import genai
from google.genai import types

from src.config import get_settings
from src.classification.prompts import RAG_CHAT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class HorizonChatAgent:
    """
    Conversational agent for querying the AI Horizon knowledge base.
    
    Uses Gemini File Search for RAG-powered responses.
    """

    def __init__(
        self,
        dcwf_store_name: Optional[str] = None,
        artifacts_store_name: Optional[str] = None,
    ):
        """
        Initialize the chat agent.
        
        Args:
            dcwf_store_name: File Search store for DCWF reference.
            artifacts_store_name: File Search store for classified artifacts.
        """
        settings = get_settings()
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_model
        
        self.dcwf_store = dcwf_store_name or settings.dcwf_store_name
        self.artifacts_store = artifacts_store_name or settings.artifacts_store_name
        
        # Conversation history
        self.history: list[dict] = []

    def chat(self, message: str) -> str:
        """
        Send a message and get a response.
        
        Args:
            message: User message.
            
        Returns:
            Assistant response.
        """
        # Build tool configuration
        stores = []
        if self.dcwf_store:
            stores.append(self.dcwf_store)
        if self.artifacts_store:
            stores.append(self.artifacts_store)
        
        tools = []
        if stores:
            tools.append(
                types.Tool(
                    file_search=types.FileSearch(
                        file_search_store_names=stores
                    )
                )
            )
        
        # Build conversation
        contents = []
        
        # Add history
        for entry in self.history:
            contents.append(types.Content(
                role=entry["role"],
                parts=[types.Part(text=entry["content"])]
            ))
        
        # Add current message
        contents.append(types.Content(
            role="user",
            parts=[types.Part(text=message)]
        ))
        
        # Generate response
        config = types.GenerateContentConfig(
            system_instruction=RAG_CHAT_SYSTEM_PROMPT,
        )
        if tools:
            config.tools = tools
        
        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=config,
        )
        
        assistant_message = response.text
        
        # Update history
        self.history.append({"role": "user", "content": message})
        self.history.append({"role": "model", "content": assistant_message})
        
        # Keep history manageable (last 20 turns)
        if len(self.history) > 40:
            self.history = self.history[-40:]
        
        return assistant_message

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.history = []

    def get_history(self) -> list[dict]:
        """Get conversation history."""
        return self.history.copy()


class HorizonAgent:
    """
    Advanced agent with tool use for AI Horizon.
    
    Supports multiple tools beyond just RAG:
    - File Search (RAG)
    - Classification
    - Export
    """

    def __init__(self):
        """Initialize the advanced agent."""
        settings = get_settings()
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_model
        self.settings = settings

    def run(self, task: str) -> str:
        """
        Execute a complex task with tool use.
        
        Args:
            task: Task description.
            
        Returns:
            Result of task execution.
        """
        # TODO: Implement advanced agentic workflows
        # For now, delegate to simple chat
        chat_agent = HorizonChatAgent()
        return chat_agent.chat(task)
