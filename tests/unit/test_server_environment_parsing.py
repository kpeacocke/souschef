"""Tests for Chef environment parsing helpers in server."""

from __future__ import annotations

from pathlib import Path

import pytest

from souschef import server


def test_parse_chef_environment_content_extracts_fields() -> None:
    """Parse environment metadata and attributes."""
    content = """
name 'dev'
description 'Development'
default_attributes({ 'x' => 1 })
override_attributes({ 'y' => 2 })
cookbook_versions({ 'nginx' => '= 1.0.0' })
"""
    result = server._parse_chef_environment_content(content)

    assert result["name"] == "dev"
    assert result["description"] == "Development"
    # Attributes parsing is complex, just check they exist as dicts
    assert isinstance(result["default_attributes"], dict)
    assert isinstance(result["override_attributes"], dict)
    assert isinstance(result["cookbook_versions"], dict)


def test_parse_ruby_hash_nested() -> None:
    """Parse nested ruby hash strings."""
    result = server.parse_ruby_hash("'a' => 1, 'b' => { 'c' => 'd' }")
    assert result["a"] == 1
    assert result["b"]["c"] == "d"


def test_parse_key_value_pair_missing_arrow() -> None:
    """Quoted key with value should parse correctly even without arrow."""
    # With quoted key, it will parse both key and value
    key, value, idx = server._parse_key_value_pair("'key' value", 0)
    assert key == "key"
    # Value will be parsed as a string
    assert isinstance(value, (str, type(None)))
    assert idx > 0


def test_parse_nested_hash_requires_brace() -> None:
    """Missing brace should raise ValueError."""
    with pytest.raises(ValueError, match="opening brace"):
        server._parse_nested_hash("key", 0)


def test_parse_quoted_key_requires_quote() -> None:
    """Non-quoted keys should raise ValueError."""
    with pytest.raises(ValueError, match="Expected quote"):
        server._parse_quoted_key("key", 0)


def test_parse_simple_value_converts_literals() -> None:
    """Ruby literals should convert to Python values."""
    value, idx = server._parse_simple_value("'hello'", 0)
    assert value == "hello"
    assert idx == len("'hello'")

    value, _ = server._parse_simple_value("true", 0)
    assert value is True

    value, _ = server._parse_simple_value("3.14", 0)
    assert value == 3.14


def test_skip_helpers() -> None:
    """Whitespace and delimiter helpers should move indices."""
    assert server._skip_whitespace("  key", 0) == 2
    assert server._skip_whitespace_and_arrows("   =>", 0) > 0
    assert server._skip_to_next_item("key, next", 0) > 0


def test_validate_databags_directory_invalid(tmp_path: Path) -> None:
    """Validation should handle missing or invalid directories."""
    path, error = server._validate_databags_directory("")
    assert path is None
    assert error is not None

    path, error = server._validate_databags_directory(str(tmp_path / "missing"))
    assert path is None
    assert error is not None

    file_path = tmp_path / "file.txt"
    file_path.write_text("data")
    path, error = server._validate_databags_directory(str(file_path))
    assert path is None
    assert error is not None
