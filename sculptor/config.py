"""Configuration loading for Open Brush AI Sculptor.

Loads settings from config.yaml with environment variable overrides.
"""

import os
from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG = {
    "llm": {
        "api_key": "",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o",
        "temperature": 0.7,
        "max_tokens": 4096,
    },
    "openbrush": {
        "host": "localhost",
        "port": 40074,
        "command_delay": 0.25,
    },
    "export": {
        "auto_save": True,
        "auto_export": False,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load configuration from YAML file with env var overrides.

    Search order for config file:
    1. Explicit path argument
    2. SCULPTOR_CONFIG env var
    3. ./config.yaml
    4. ~/.config/sculptor/config.yaml

    Environment variable overrides:
    - OPENAI_API_KEY -> llm.api_key
    - OPENAI_BASE_URL -> llm.base_url
    - OPENAI_MODEL -> llm.model
    - OPENBRUSH_HOST -> openbrush.host
    - OPENBRUSH_PORT -> openbrush.port
    """
    config = DEFAULT_CONFIG.copy()

    # Find config file
    if config_path is None:
        config_path = os.environ.get("SCULPTOR_CONFIG")

    if config_path is None:
        candidates = [
            Path("config.yaml"),
            Path.home() / ".config" / "sculptor" / "config.yaml",
        ]
        for candidate in candidates:
            if candidate.exists():
                config_path = candidate
                break

    # Load YAML if found
    if config_path is not None:
        path = Path(config_path)
        if path.exists():
            with open(path) as f:
                file_config = yaml.safe_load(f) or {}
            config = _deep_merge(config, file_config)

    # Environment variable overrides
    env_overrides = {
        "OPENAI_API_KEY": ("llm", "api_key"),
        "OPENAI_BASE_URL": ("llm", "base_url"),
        "OPENAI_MODEL": ("llm", "model"),
        "OPENBRUSH_HOST": ("openbrush", "host"),
        "OPENBRUSH_PORT": ("openbrush", "port"),
    }

    for env_var, key_path in env_overrides.items():
        value = os.environ.get(env_var)
        if value is not None:
            section, key = key_path
            if section not in config:
                config[section] = {}
            # Convert port to int
            if key == "port":
                value = int(value)
            config[section][key] = value

    return config


def validate_config(config: dict) -> list[str]:
    """Validate config and return list of issues."""
    issues = []

    if not config.get("llm", {}).get("api_key"):
        issues.append(
            "LLM API key not set. Set it in config.yaml or via OPENAI_API_KEY env var."
        )

    return issues
