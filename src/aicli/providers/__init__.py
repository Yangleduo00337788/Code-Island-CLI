"""AI model providers."""

from typing import Optional

from .base import BaseProvider, Message, ChatResponse
from .openai_provider import OpenAIProvider
from .claude_provider import ClaudeProvider
from .ollama_provider import OllamaProvider

__all__ = [
    "BaseProvider",
    "OpenAIProvider",
    "ClaudeProvider",
    "OllamaProvider",
    "Message",
    "ChatResponse",
    "create_provider",
]


def create_provider(
    provider_name: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> BaseProvider:
    """Create a provider instance based on provider name.

    Args:
        provider_name: Name of the provider (deepseek, openai, claude, ollama, etc.)
        api_key: API key for the provider
        base_url: Base URL for the provider API

    Returns:
        Provider instance
    """
    if provider_name in ("deepseek", "openai", "moonshot"):
        return OpenAIProvider(
            api_key=api_key,
            base_url=base_url,
            provider_name=provider_name,
        )
    elif provider_name == "claude":
        return ClaudeProvider(api_key=api_key, base_url=base_url)
    elif provider_name == "ollama":
        return OllamaProvider(api_key=api_key, base_url=base_url)
    else:
        raise ValueError(f"未知提供商: {provider_name}")
