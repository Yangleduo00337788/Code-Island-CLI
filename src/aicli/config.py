"""Configuration management for aicli."""

import os
from pathlib import Path
from typing import Optional

import toml
from pydantic import BaseModel, Field


class ProviderConfig(BaseModel):
    """Configuration for a single AI provider."""

    api_key: Optional[str] = None
    base_url: Optional[str] = None
    default_model: Optional[str] = None


class AppConfig(BaseModel):
    """Main application configuration."""

    default_provider: str = "deepseek"
    default_model: str = "deepseek-chat"
    stream: bool = True
    history_size: int = 100
    auto_approve: bool = False
    providers: dict[str, ProviderConfig] = Field(default_factory=dict)


def get_config_dir() -> Path:
    """Get the configuration directory path."""
    if os.name == "nt":
        config_dir = Path(os.environ.get("APPDATA", "~")) / "aicli"
    else:
        config_dir = Path.home() / ".config" / "aicli"
    return config_dir


def get_config_file() -> Path:
    """Get the configuration file path."""
    return get_config_dir() / "config.toml"


def load_config_file() -> dict:
    """Load configuration from TOML file."""
    config_file = get_config_file()
    if not config_file.exists():
        return {}
    try:
        return toml.load(config_file)
    except Exception:
        return {}


def save_config(config: AppConfig) -> None:
    """Save configuration to TOML file."""
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = get_config_file()

    data = config.model_dump()
    with open(config_file, "w", encoding="utf-8") as f:
        toml.dump(data, f)


def load_config(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    stream: Optional[bool] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> AppConfig:
    """Load configuration with priority: CLI args > env vars > config file."""

    # Start with config file
    file_config = load_config_file()
    config = AppConfig(**file_config)

    # Override with environment variables
    env_provider = os.environ.get("AICLI_PROVIDER")
    if env_provider:
        config.default_provider = env_provider

    env_model = os.environ.get("AICLI_MODEL")
    if env_model:
        config.default_model = env_model

    env_stream = os.environ.get("AICLI_STREAM")
    if env_stream is not None:
        config.stream = env_stream.lower() in ("true", "1", "yes")

    # Load API keys from environment
    env_keys = {
        "deepseek": "DEEPSEEK_API_KEY",
        "openai": "OPENAI_API_KEY",
        "claude": "ANTHROPIC_API_KEY",
    }

    for provider_name, env_var in env_keys.items():
        key = os.environ.get(env_var)
        if key:
            if provider_name not in config.providers:
                config.providers[provider_name] = ProviderConfig()
            config.providers[provider_name].api_key = key

    # Override with CLI arguments
    if provider:
        config.default_provider = provider
    if model:
        config.default_model = model
    if stream is not None:
        config.stream = stream
    if api_key:
        if config.default_provider not in config.providers:
            config.providers[config.default_provider] = ProviderConfig()
        config.providers[config.default_provider].api_key = api_key
    if base_url:
        if config.default_provider not in config.providers:
            config.providers[config.default_provider] = ProviderConfig()
        config.providers[config.default_provider].base_url = base_url

    return config


def get_provider_config(config: AppConfig, provider_name: str) -> ProviderConfig:
    """Get configuration for a specific provider."""
    if provider_name in config.providers:
        return config.providers[provider_name]
    return ProviderConfig()
