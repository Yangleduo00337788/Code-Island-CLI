"""Tests for configuration module."""

import os
from pathlib import Path

import pytest

from aicli.config import AppConfig, load_config, get_config_dir


def test_default_config():
    """Test default configuration values."""
    config = AppConfig()
    assert config.default_provider == "deepseek"
    assert config.default_model == "deepseek-chat"
    assert config.stream is True
    assert config.history_size == 100


def test_config_dir():
    """Test config directory exists."""
    config_dir = get_config_dir()
    assert isinstance(config_dir, Path)


def test_load_config_with_args():
    """Test loading config with CLI arguments."""
    config = load_config(provider="openai", model="gpt-4o")
    assert config.default_provider == "openai"
    assert config.default_model == "gpt-4o"


def test_load_config_with_env(monkeypatch):
    """Test loading config with environment variables."""
    monkeypatch.setenv("AICLI_PROVIDER", "claude")
    monkeypatch.setenv("AICLI_MODEL", "claude-3-5-sonnet-20241022")

    config = load_config()
    assert config.default_provider == "claude"
    assert config.default_model == "claude-3-5-sonnet-20241022"
