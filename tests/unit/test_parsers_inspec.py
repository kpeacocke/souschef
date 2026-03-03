"""Tests for parsers/inspec.py module."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from souschef.parsers.inspec import (
    _parse_controls_from_directory,
    _parse_controls_from_file,
    convert_inspec_to_test,
    generate_inspec_from_chef,
    parse_inspec_profile,
)


def test_parse_inspec_profile_path_traversal_blocked(tmp_path: Path) -> None:
    """Path traversal attempts should be blocked."""
    # Mock _ensure_within_base_path to always raise ValueError
    with patch(
        "souschef.parsers.inspec._ensure_within_base_path",
        side_effect=ValueError("Path outside base"),
    ):
        result = parse_inspec_profile("../../etc/passwd")
    assert "Error: Path traversal attempt detected" in result
    assert "Suggestion:" in result


def test_parse_inspec_profile_empty_path() -> None:
    """Empty path should return error."""
    result = parse_inspec_profile("")
    assert "Error: Path cannot be empty" in result
    assert "Suggestion:" in result


def test_parse_inspec_profile_whitespace_only_path() -> None:
    """Whitespace-only path should return error."""
    result = parse_inspec_profile("   ")
    assert "Error: Path cannot be empty" in result
    assert "Suggestion:" in result


def test_parse_inspec_profile_invalid_path_type(tmp_path: Path) -> None:
    """Invalid path types (not file or directory) should return error."""
    # Create a named pipe or socket (special file type)
    import os

    fifo_path = tmp_path / "test_fifo"
    try:
        os.mkfifo(fifo_path)

        # Patch _normalize_path to return the fifo path
        with (
            patch("souschef.parsers.inspec._normalize_path", return_value=fifo_path),
            patch(
                "souschef.parsers.inspec._ensure_within_base_path",
                return_value=fifo_path,
            ),
            patch("souschef.parsers.inspec.Path.exists", return_value=True),
            patch("souschef.parsers.inspec.Path.is_dir", return_value=False),
            patch("souschef.parsers.inspec.Path.is_file", return_value=False),
        ):
            result = parse_inspec_profile(str(fifo_path))

        assert "Error: Invalid path type:" in result
        assert "Suggestion:" in result
    finally:
        if fifo_path.exists():
            fifo_path.unlink()


def test_parse_inspec_profile_file_not_found_error() -> None:
    """FileNotFoundError should be caught and return error message."""
    with patch(
        "souschef.parsers.inspec._normalize_path",
        side_effect=FileNotFoundError("File not found"),
    ):
        result = parse_inspec_profile("/some/path")
        assert "Error: File not found" in result
        assert "Suggestion:" in result


def test_parse_inspec_profile_runtime_error() -> None:
    """RuntimeError should be caught and return error message."""
    with patch(
        "souschef.parsers.inspec._normalize_path",
        side_effect=RuntimeError("Runtime error"),
    ):
        result = parse_inspec_profile("/some/path")
        assert "Error: Runtime error" in result
        assert "Suggestion:" in result


def test_parse_inspec_profile_generic_exception() -> None:
    """Generic exceptions should be caught and return error message."""
    with patch(
        "souschef.parsers.inspec._normalize_path",
        side_effect=ValueError("Unexpected error"),
    ):
        result = parse_inspec_profile("/some/path")
        assert "An error occurred while parsing InSpec profile:" in result


def test_convert_inspec_to_test_unsupported_format() -> None:
    """Unsupported output formats should return error."""
    with patch(
        "souschef.parsers.inspec.parse_inspec_profile",
        return_value=json.dumps({"controls": [{"id": "test"}]}),
    ):
        result = convert_inspec_to_test("/some/path", "unsupported_format")
        assert "Error: Unsupported format 'unsupported_format'" in result
        assert "Use 'testinfra', 'ansible_assert', 'serverspec', or 'goss'" in result


def test_convert_inspec_to_test_json_decode_error() -> None:
    """JSONDecodeError should be caught and return error message."""
    with patch(
        "souschef.parsers.inspec.parse_inspec_profile",
        return_value="invalid json {{{",
    ):
        result = convert_inspec_to_test("/some/path", "testinfra")
        assert "Error parsing InSpec result:" in result


def test_convert_inspec_to_test_generic_exception() -> None:
    """Generic exceptions should be caught and return error message."""
    with patch(
        "souschef.parsers.inspec.parse_inspec_profile",
        side_effect=RuntimeError("Unexpected error"),
    ):
        result = convert_inspec_to_test("/some/path", "testinfra")
        assert "An error occurred during conversion:" in result


def test_generate_inspec_from_chef_returns_result() -> None:
    """generate_inspec_from_chef should delegate to internal function."""
    with patch(
        "souschef.parsers.inspec._generate_inspec_from_resource",
        return_value="control 'test' do\nend",
    ) as mock_gen:
        result = generate_inspec_from_chef("package", "nginx", {"version": "1.18.0"})

        assert result == "control 'test' do\nend"
        mock_gen.assert_called_once_with("package", "nginx", {"version": "1.18.0"})


def test_convert_inspec_to_goss_yaml_import_error() -> None:
    """Goss conversion should fallback to JSON when PyYAML unavailable."""
    mock_controls = [
        {
            "id": "test-1",
            "title": "Test Control",
            "tests": [
                {
                    "resource_type": "package",
                    "resource_name": "nginx",
                    "expectations": [{"matcher": "be_installed", "negated": False}],
                }
            ],
        }
    ]

    with patch(
        "souschef.parsers.inspec.parse_inspec_profile",
        return_value=json.dumps({"controls": mock_controls}),
    ):
        # Temporarily remove yaml from sys.modules to simulate ImportError
        yaml_module = sys.modules.get("yaml")
        if "yaml" in sys.modules:
            del sys.modules["yaml"]

        try:
            # Mock the import to raise ImportError
            import builtins

            real_import = builtins.__import__

            def mock_import(name, *args, **kwargs):
                if name == "yaml":
                    raise ImportError("No module named yaml")
                return real_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=mock_import):
                result = convert_inspec_to_test("/some/path", "goss")

            # Should fall back to JSON format
            assert "{" in result
            assert '"package"' in result or "'package'" in result
        finally:
            # Restore yaml module if it was there
            if yaml_module is not None:
                sys.modules["yaml"] = yaml_module


def test_parse_controls_from_directory_read_error(tmp_path: Path) -> None:
    """Read errors in control files should raise RuntimeError."""
    controls_dir = tmp_path / "controls"
    controls_dir.mkdir()
    control_file = controls_dir / "default.rb"
    control_file.write_text("control 'x' do end")

    with (
        patch(
            "souschef.parsers.inspec.safe_read_text", side_effect=OSError("read failed")
        ),
        pytest.raises(RuntimeError, match="Error reading"),
    ):
        _parse_controls_from_directory(tmp_path)


def test_parse_controls_from_file_read_error(tmp_path: Path) -> None:
    """Read errors in control file should raise RuntimeError."""
    control_file = tmp_path / "control.rb"
    control_file.write_text("control 'x' do end")

    with (
        patch("pathlib.Path.read_text", side_effect=OSError("read failed")),
        pytest.raises(RuntimeError, match="Error reading file"),
    ):
        _parse_controls_from_file(control_file)
