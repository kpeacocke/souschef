"""Edge case tests for Chef attributes parser helpers."""

from souschef.parsers.attributes import (
    _collect_multiline_value,
    _convert_ruby_hash,
    _extract_attributes,
    _extract_precedence_and_path,
    _is_value_complete,
    _update_string_state,
)


def test_extract_precedence_unknown_returns_none() -> None:
    """Test unknown precedence values are ignored."""
    assert _extract_precedence_and_path("custom['a'] = 1") is None


def test_extract_precedence_defensive_else_clause() -> None:
    """Test defensive else clause when precedence type exists but isn't handled."""
    # Inject a custom precedence type that isn't in the if/elif chain
    # This tests the defensive programming at the else clause
    custom_types = ("default", "custom_precedence", "override")
    result = _extract_precedence_and_path(
        "custom_precedence['x'] = 1",
        _precedence_types=custom_types,
    )

    # Should return None because 'custom_precedence' passes tuple check
    # but isn't in the if/elif chain
    assert result is None


def test_update_string_state_starts_string() -> None:
    """Test string parsing starts when a quote is encountered."""
    in_string, string_char = _update_string_state("'", False, None, "'", [])

    assert in_string is True
    assert string_char == "'"


def test_is_value_complete_for_percent_w() -> None:
    """Test %w value detection completes on closing paren."""
    completed = _is_value_complete(
        in_string=False,
        brace_depth=0,
        bracket_depth=0,
        paren_depth=0,
        value_lines=["%w("],
        line=")",
        next_line="",
        precedence_types=("default",),
    )

    assert completed is True


def test_collect_multiline_value_skips_leading_empty() -> None:
    """Test multiline collection skips leading empty lines."""
    lines = ["", "  'value'"]
    value, index = _collect_multiline_value(lines, 0)

    assert index >= 1
    assert "value" in value


def test_convert_ruby_hash_empty() -> None:
    """Test empty Ruby hash converts to empty YAML mapping."""
    assert _convert_ruby_hash("{}") == "{}"


def test_extract_attributes_reconstructs_multiline_word_array() -> None:
    """Test multiline %w arrays are reconstructed correctly."""
    content = """
    default['app']['packages'] = %w(
      nginx
      redis
    )
    """
    attributes = _extract_attributes(content)

    assert attributes
    # Value should be converted to YAML list format
    assert "- nginx" in attributes[0]["value"]
    assert "- redis" in attributes[0]["value"]
