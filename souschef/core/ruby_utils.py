"""
Ruby value normalization utilities for Chef-to-Ansible conversion.

This module provides utilities for normalizing Ruby values and syntax
during the conversion process from Chef to Ansible.
"""

import re


def _normalize_ruby_value(value: str) -> str:
    """
    Normalize Ruby value representation.

    Converts Ruby-specific syntax to a normalized string representation
    suitable for Ansible playbooks.

    Args:
        value: Raw Ruby value string.

    Returns:
        Normalized value string.

    Examples:
        >>> _normalize_ruby_value(":symbol")
        '"symbol"'
        >>> _normalize_ruby_value("[:a, :b]")
        '["a", "b"]'

    """
    value = value.strip()
    # Handle symbols: :symbol -> "symbol"
    if value.startswith(":") and value[1:].replace("_", "").isalnum():
        return f'"{value[1:]}"'
    # Handle arrays: [:a, :b] -> ["a", "b"]
    if value.startswith("[") and value.endswith("]"):
        # Simple symbol array conversion
        value = re.sub(r":(\w+)", r'"\1"', value)
    return value
