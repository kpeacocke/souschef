"""
Shared AI environment configuration utilities for SousChef UI pages.

Provides a single implementation of loading AI provider settings from
environment variables, shared between the AI Settings and Cookbook
Analysis pages.
"""

import os
from contextlib import suppress


def _load_ai_settings_from_env(
    *, include_api_key: bool = True
) -> dict[str, str | float | int]:
    """
    Load AI provider settings from environment variables.

    Args:
        include_api_key: When True (default), the ``SOUSCHEF_AI_API_KEY``
            environment variable is included in the result.  Set to False
            in contexts where the API key must not be stored in a plain
            dictionary to prevent accidental logging or exposure.

    Returns:
        Dictionary of AI settings loaded from the environment.

    """
    env_config: dict[str, str | float | int] = {}
    env_mappings: dict[str, str] = {
        "SOUSCHEF_AI_PROVIDER": "provider",
        "SOUSCHEF_AI_MODEL": "model",
        "SOUSCHEF_AI_BASE_URL": "base_url",
        "SOUSCHEF_AI_PROJECT_ID": "project_id",
    }
    if include_api_key:
        env_mappings["SOUSCHEF_AI_API_KEY"] = "api_key"

    # Handle string values
    for env_var, config_key in env_mappings.items():
        env_value = os.environ.get(env_var)
        if env_value:
            env_config[config_key] = env_value

    # Handle numeric values with error suppression
    temp_value = os.environ.get("SOUSCHEF_AI_TEMPERATURE")
    if temp_value:
        with suppress(ValueError):
            env_config["temperature"] = float(temp_value)

    tokens_value = os.environ.get("SOUSCHEF_AI_MAX_TOKENS")
    if tokens_value:
        with suppress(ValueError):
            env_config["max_tokens"] = int(tokens_value)

    return env_config
