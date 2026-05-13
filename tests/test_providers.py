"""Tests for providers module."""

import pytest

from aicli.providers import create_provider, OpenAIProvider, ClaudeProvider, OllamaProvider


def test_create_openai_provider():
    """Test creating OpenAI provider."""
    provider = create_provider("openai", api_key="test-key")
    assert isinstance(provider, OpenAIProvider)
    assert provider.api_key == "test-key"


def test_create_deepseek_provider():
    """Test creating DeepSeek provider."""
    provider = create_provider("deepseek", api_key="test-key")
    assert isinstance(provider, OpenAIProvider)
    assert provider.base_url == "https://api.deepseek.com"


def test_create_claude_provider():
    """Test creating Claude provider."""
    provider = create_provider("claude", api_key="test-key")
    assert isinstance(provider, ClaudeProvider)


def test_create_ollama_provider():
    """Test creating Ollama provider."""
    provider = create_provider("ollama")
    assert isinstance(provider, OllamaProvider)
    assert provider.validate_api_key() is True


def test_create_unknown_provider():
    """Test creating unknown provider raises error."""
    with pytest.raises(ValueError, match="Unknown provider"):
        create_provider("unknown")


def test_openai_models():
    """Test OpenAI provider models."""
    provider = OpenAIProvider(api_key="test", provider_name="openai")
    models = provider.get_available_models()
    assert "gpt-4o" in models


def test_deepseek_models():
    """Test DeepSeek provider models."""
    provider = OpenAIProvider(api_key="test", provider_name="deepseek")
    models = provider.get_available_models()
    assert "deepseek-chat" in models


def test_claude_models():
    """Test Claude provider models."""
    provider = ClaudeProvider(api_key="test")
    models = provider.get_available_models()
    assert "claude-3-5-sonnet-20241022" in models
