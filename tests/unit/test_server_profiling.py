"""Tests for server profiling tools."""

from unittest.mock import MagicMock, patch

from souschef.server import profile_parsing_operation


def test_profile_parsing_operation_invalid() -> None:
    """Invalid operation returns supported operations list."""
    result = profile_parsing_operation("invalid", "/tmp/file.rb")

    assert "Invalid operation" in result
    assert "Supported operations" in result


def test_profile_parsing_operation_basic() -> None:
    """Basic profiling returns profile output string."""
    mock_profile = MagicMock()
    mock_profile.__str__.return_value = "profile result"  # type: ignore[attr-defined]

    with patch(
        "souschef.profiling.profile_function",
        return_value=(None, mock_profile),
    ):
        result = profile_parsing_operation("recipe", "/tmp/file.rb", detailed=False)

    assert "profile result" in result


def test_profile_parsing_operation_detailed() -> None:
    """Detailed profiling includes top functions when present."""
    mock_profile = MagicMock()
    mock_profile.__str__.return_value = "profile result"  # type: ignore[attr-defined]
    mock_profile.function_stats = {"top_functions": "top list"}

    with patch(
        "souschef.profiling.detailed_profile_function",
        return_value=(None, mock_profile),
    ):
        result = profile_parsing_operation("attributes", "/tmp/file.rb", detailed=True)

    assert "profile result" in result
    assert "Detailed Function Statistics" in result
    assert "top list" in result


def test_profile_parsing_operation_error() -> None:
    """Profiling errors are formatted with context."""
    with patch(
        "souschef.profiling.profile_function",
        side_effect=RuntimeError("boom"),
    ):
        result = profile_parsing_operation("template", "/tmp/file.rb", detailed=False)

    assert "profiling template parsing" in result
    assert "boom" in result
