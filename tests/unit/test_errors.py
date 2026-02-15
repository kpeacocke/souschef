"""Tests for error handling and message sanitization."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from souschef.core.errors import (
    ChefFileNotFoundError,
    InvalidCookbookError,
    ParseError,
    _is_debug_mode,
    _sanitize_path,
    format_error_with_context,
)


class TestDebugMode:
    """Test debug mode detection."""

    def test_debug_mode_disabled_by_default(self) -> None:
        """Test that debug mode is disabled by default."""
        with patch.dict(os.environ, {}, clear=True):
            assert _is_debug_mode() is False

    @pytest.mark.parametrize(
        "debug_value",
        ["1", "true", "True", "TRUE", "yes", "Yes", "YES", "on", "On", "ON"],
    )
    def test_debug_mode_enabled(self, debug_value: str) -> None:
        """Test that debug mode is enabled with various truthy values."""
        with patch.dict(os.environ, {"SOUSCHEF_DEBUG": debug_value}):
            assert _is_debug_mode() is True

    @pytest.mark.parametrize("debug_value", ["0", "false", "no", "off", "invalid"])
    def test_debug_mode_disabled(self, debug_value: str) -> None:
        """Test that debug mode is disabled with falsy values."""
        with patch.dict(os.environ, {"SOUSCHEF_DEBUG": debug_value}):
            assert _is_debug_mode() is False


class TestPathSanitization:
    """Test path sanitization for error messages."""

    def test_sanitize_absolute_path_production_mode(self, tmp_path: Path) -> None:
        """Test that absolute paths are sanitized in production mode."""
        test_file = tmp_path / "test_cookbook" / "recipes" / "default.rb"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("# test content")

        with patch.dict(os.environ, {}, clear=True):
            # Change to parent directory
            original_cwd = Path.cwd()
            try:
                os.chdir(tmp_path)
                sanitized = _sanitize_path(str(test_file))
                # Should be relative to cwd
                assert sanitized == "test_cookbook/recipes/default.rb"
                # Should not contain absolute path components
                assert not sanitized.startswith("/")
                assert "tmp" not in sanitized.lower()
            finally:
                os.chdir(original_cwd)

    def test_sanitize_path_outside_cwd_production_mode(self) -> None:
        """Test that paths outside cwd return generic placeholder in production."""
        with patch.dict(os.environ, {}, clear=True):
            # Path far from cwd
            test_path = "/etc/passwd"
            sanitized = _sanitize_path(test_path)
            # Should return generic placeholder to avoid confusing truncation
            assert sanitized == "<file>"

    def test_sanitize_path_debug_mode(self, tmp_path: Path) -> None:
        """Test that full paths are shown in debug mode."""
        test_file = tmp_path / "test_cookbook" / "recipes" / "default.rb"

        with patch.dict(os.environ, {"SOUSCHEF_DEBUG": "1"}):
            sanitized = _sanitize_path(str(test_file))
            # Should be full path
            assert sanitized == str(test_file)

    def test_sanitize_path_handles_path_objects(self, tmp_path: Path) -> None:
        """Test that Path objects are handled correctly."""
        test_file = tmp_path / "cookbook" / "recipes" / "default.rb"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("# test")

        with patch.dict(os.environ, {}, clear=True):
            original_cwd = Path.cwd()
            try:
                os.chdir(tmp_path)
                sanitized = _sanitize_path(test_file)
                assert sanitized == "cookbook/recipes/default.rb"
            finally:
                os.chdir(original_cwd)

    def test_sanitize_path_handles_errors_gracefully(self) -> None:
        """Test that invalid paths return placeholder."""
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("souschef.core.errors.Path") as mock_path,
        ):
            # Test with None (should handle gracefully)
            mock_path.side_effect = Exception("Path error")
            sanitized = _sanitize_path("any_path")
            assert sanitized == "<file>"

    def test_sanitize_path_rejects_json_objects(self) -> None:
        """Test that JSON objects are treated as non-path inputs."""
        with patch.dict(os.environ, {}, clear=True):
            json_input = '{"error": "file not found"}'
            sanitized = _sanitize_path(json_input)
            assert sanitized == "<resource>"

    def test_sanitize_path_rejects_json_arrays(self) -> None:
        """Test that JSON arrays are treated as non-path inputs."""
        with patch.dict(os.environ, {}, clear=True):
            json_input = '["file1.txt", "file2.txt"]'
            sanitized = _sanitize_path(json_input)
            assert sanitized == "<resource>"

    def test_sanitize_path_rejects_multiline_input(self) -> None:
        """Test that multiline input is treated as non-path."""
        with patch.dict(os.environ, {}, clear=True):
            multiline = "file1.txt\nfile2.txt"
            sanitized = _sanitize_path(multiline)
            assert sanitized == "<resource>"

    def test_sanitize_path_rejects_urls(self) -> None:
        """Test that URLs with schemes are treated as non-path inputs."""
        with patch.dict(os.environ, {}, clear=True):
            url = "http://example.com/path/to/file"
            sanitized = _sanitize_path(url)
            assert sanitized == "<resource>"

    def test_sanitize_path_accepts_relative_paths_with_slashes(self) -> None:
        """Test that relative paths with slashes are still processed normally."""
        with patch.dict(os.environ, {}, clear=True):
            relative_path = "config/recipes/default.rb"
            sanitized = _sanitize_path(relative_path)
            # Should not be replaced with <resource> just for having slashes
            assert sanitized != "<resource>"


class TestErrorMessageSanitization:
    """Test error message sanitization."""

    def test_file_not_found_error_production_mode(self, tmp_path: Path) -> None:
        """Test ChefFileNotFoundError sanitizes paths in production."""
        test_path = tmp_path / "deep" / "nested" / "cookbook" / "metadata.rb"

        with patch.dict(os.environ, {}, clear=True):
            error = ChefFileNotFoundError(str(test_path), "cookbook")
            error_msg = str(error)

            # Should not contain full path
            assert str(tmp_path) not in error_msg
            # Should not contain "Debug:" section
            assert "Debug:" not in error_msg
            # Should contain relative path or basename
            assert "metadata.rb" in error_msg or "cookbook" in error_msg

    def test_file_not_found_error_debug_mode(self, tmp_path: Path) -> None:
        """Test ChefFileNotFoundError shows full path in debug mode."""
        test_path = tmp_path / "deep" / "nested" / "cookbook" / "metadata.rb"

        with patch.dict(os.environ, {"SOUSCHEF_DEBUG": "1"}):
            error = ChefFileNotFoundError(str(test_path), "cookbook")
            error_msg = str(error)

            # Should contain full path in debug section
            assert "Debug: Full path attempted:" in error_msg
            assert str(test_path) in error_msg

    def test_invalid_cookbook_error_production_mode(self, tmp_path: Path) -> None:
        """Test InvalidCookbookError sanitizes paths in production."""
        test_path = tmp_path / "some" / "cookbook"

        with patch.dict(os.environ, {}, clear=True):
            original_cwd = Path.cwd()
            try:
                os.chdir(tmp_path)
                error = InvalidCookbookError(str(test_path), "missing metadata")
                error_msg = str(error)

                # Should use relative path
                assert "some/cookbook" in error_msg
                # Should not have debug info
                assert "Debug:" not in error_msg
            finally:
                os.chdir(original_cwd)

    def test_parse_error_production_mode(self, tmp_path: Path) -> None:
        """Test ParseError sanitizes paths in production."""
        test_file = tmp_path / "cookbook" / "recipes" / "default.rb"

        with patch.dict(os.environ, {}, clear=True):
            error = ParseError(str(test_file), 42, "syntax error")
            error_msg = str(error)

            # Should not contain full absolute path
            assert str(tmp_path) not in error_msg or "Debug:" in error_msg
            # Should mention file info (either filename or generic placeholder)
            assert "default.rb" in error_msg or "<file>" in error_msg
            # Should mention line number
            assert "42" in error_msg

    def test_parse_error_debug_mode(self, tmp_path: Path) -> None:
        """Test ParseError shows full path in debug mode."""
        test_file = tmp_path / "cookbook" / "recipes" / "default.rb"

        with patch.dict(os.environ, {"SOUSCHEF_DEBUG": "1"}):
            error = ParseError(str(test_file), 42, "syntax error")
            error_msg = str(error)

            # Should contain full path in debug section
            assert "Debug: Full path:" in error_msg
            assert str(test_file) in error_msg

    def test_format_error_with_context_production_mode(self, tmp_path: Path) -> None:
        """Test format_error_with_context sanitizes paths in production."""
        test_file = tmp_path / "recipes" / "default.rb"

        with patch.dict(os.environ, {}, clear=True):
            original_cwd = Path.cwd()
            try:
                os.chdir(tmp_path)
                error = ValueError("Invalid value")
                formatted = format_error_with_context(
                    error, "parsing recipe", str(test_file)
                )

                # Should use relative path
                assert "recipes/default.rb" in formatted
                # Should not contain absolute path
                assert str(tmp_path) not in formatted
            finally:
                os.chdir(original_cwd)

    def test_format_error_with_context_debug_mode(self, tmp_path: Path) -> None:
        """Test format_error_with_context shows full info in debug mode."""
        test_file = tmp_path / "recipes" / "default.rb"
        error = RuntimeError("Something went wrong")

        with patch.dict(os.environ, {"SOUSCHEF_DEBUG": "1"}):
            formatted = format_error_with_context(
                error, "processing file", str(test_file)
            )

            # Should contain debug information
            assert "Debug:" in formatted
            # Should show error representation
            assert "RuntimeError" in formatted or "Something went wrong" in formatted

    def test_format_error_preserves_souschef_errors(self) -> None:
        """Test that SousChefError instances are returned as-is."""
        error = ParseError("/some/file.rb", 10, "test error")

        with patch.dict(os.environ, {}, clear=True):
            formatted = format_error_with_context(error, "testing")
            # Should return the original error's string representation
            assert formatted == str(error)

    def test_permission_error_production_mode(self, tmp_path: Path) -> None:
        """Test PermissionError sanitizes path in production."""
        test_file = tmp_path / "restricted" / "file.rb"

        with patch.dict(os.environ, {}, clear=True):
            original_cwd = Path.cwd()
            try:
                os.chdir(tmp_path)
                error = PermissionError("Access denied")
                formatted = format_error_with_context(
                    error, "reading file", str(test_file)
                )

                # Should use relative path
                assert "restricted/file.rb" in formatted
                # Should not have debug section
                assert "Debug:" not in formatted
            finally:
                os.chdir(original_cwd)

    def test_permission_error_debug_mode(self, tmp_path: Path) -> None:
        """Test PermissionError shows full path in debug mode."""
        test_file = tmp_path / "restricted" / "file.rb"

        with patch.dict(os.environ, {"SOUSCHEF_DEBUG": "1"}):
            error = PermissionError("Access denied")
            formatted = format_error_with_context(error, "reading file", str(test_file))

            # Should contain full path in debug section
            assert "Debug: Full path:" in formatted
            assert str(test_file) in formatted
