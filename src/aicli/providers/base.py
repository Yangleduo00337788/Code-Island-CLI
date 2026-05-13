"""Base provider interface for AI models."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator, Optional


@dataclass
class Message:
    """Chat message."""

    role: str
    content: str
    tool_calls: Optional[list] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None
    reasoning_content: Optional[str] = None


@dataclass
class ChatResponse:
    """Response from AI model."""

    content: str
    model: str
    usage: Optional[dict] = None
    tool_calls: Optional[list] = None
    reasoning_content: Optional[str] = None


class BaseProvider(ABC):
    """Abstract base class for AI providers."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url

    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        model: str,
        stream: bool = False,
        tools: Optional[list] = None,
    ) -> ChatResponse | AsyncIterator[str]:
        """Send chat messages to the AI model.

        Args:
            messages: List of chat messages
            model: Model name to use
            stream: Whether to stream the response
            tools: List of tool definitions for function calling

        Returns:
            ChatResponse or AsyncIterator[str] for streaming
        """
        pass

    @abstractmethod
    def get_available_models(self) -> list[str]:
        """Get list of available models."""
        pass

    def validate_api_key(self) -> bool:
        """Validate that API key is configured."""
        return self.api_key is not None and len(self.api_key) > 0
