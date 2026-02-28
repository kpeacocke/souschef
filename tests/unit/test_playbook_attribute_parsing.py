"""Tests for Chef attribute parsing helpers."""

from souschef.converters.playbook import (
    _collect_value_lines,
    _extract_attribute_variables,
    _find_and_collect_value_lines,
    _is_attribute_separator,
)


def test_is_attribute_separator_matches_prefixes() -> None:
    """Test attribute separator detection for known prefixes."""
    assert _is_attribute_separator("Attribute: app.port") is True
    assert _is_attribute_separator("Precedence: default") is True
    assert _is_attribute_separator("=") is True
    assert _is_attribute_separator("Total attributes: 3") is True
    assert _is_attribute_separator("Value: 123") is False


def test_collect_value_lines_until_separator() -> None:
    """Test value line collection stops at next attribute separator."""
    lines = [
        "first line",
        "second line",
        "Attribute: app.port",
        "Value: 8080",
    ]
    value_lines, next_index = _collect_value_lines(lines, 0)

    assert value_lines == ["first line", "second line"]
    assert next_index == 2


def test_find_and_collect_value_lines_single_line() -> None:
    """Test finding a single-line value block."""
    lines = [
        "Attribute: app.port",
        "Value: 8080",
        "Attribute: app.enabled",
        "Value: true",
    ]
    value_lines, next_index = _find_and_collect_value_lines(lines, 1)

    assert value_lines
    assert value_lines[0].strip() == "8080"
    assert next_index == 2


def test_find_and_collect_value_lines_multiline() -> None:
    """Test finding a multi-line value block."""
    lines = [
        "Attribute: app.config",
        "Value: line1",
        "line2",
        "line3",
        "Attribute: app.other",
        "Value: next",
    ]
    value_lines, next_index = _find_and_collect_value_lines(lines, 1)

    assert [value.strip() for value in value_lines] == ["line1", "line2", "line3"]
    assert next_index == 4


def test_extract_attribute_variables_basic() -> None:
    """Test extracting basic attribute variables."""
    content = """Attribute: app.port
Value: 8080
Attribute: app.enabled
Value: true
"""
    variables = _extract_attribute_variables(content)

    assert variables["app_port"] == "8080"
    assert variables["app_enabled"] == "true"


def test_extract_attribute_variables_multiline_values() -> None:
    """Test extracting attributes with multi-line values."""
    content = """Attribute: app.config
Value: line1
line2
line3
Attribute: app.mode
Value: production
"""
    variables = _extract_attribute_variables(content)

    assert "app_config" in variables
    assert "line1" in variables["app_config"]
    assert "line2" in variables["app_config"]
    assert variables["app_mode"] == '"production"'


def test_extract_attribute_variables_missing_value() -> None:
    """Test attributes without values are skipped."""
    content = """Attribute: app.missing
Attribute: app.present
Value: yes
"""
    variables = _extract_attribute_variables(content)

    assert "app_missing" not in variables
    assert variables["app_present"] == '"yes"'
