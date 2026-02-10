"""Tests for error handling paths in souschef.server."""

import tempfile
from pathlib import Path

from souschef.server import (
    parse_custom_resource,
    parse_template,
    read_file,
)


class TestFileErrorHandling:
    """Test error handling for file operations."""

    def test_parse_template_is_directory_error(self, tmp_path):
        """Test parse_template when path is a directory."""
        directory = tmp_path / "templates"
        directory.mkdir()

        result = parse_template(str(directory))

        assert "Error:" in result
        assert "directory" in result.lower()

    def test_parse_custom_resource_is_directory_error(self, tmp_path):
        """Test parse_custom_resource when path is a directory."""
        directory = tmp_path / "resources"
        directory.mkdir()

        result = parse_custom_resource(str(directory))

        assert "Error:" in result
        assert "directory" in result.lower()

    def test_read_file_is_directory_error(self, tmp_path, monkeypatch):
        """Test read_file when path is a directory."""
        directory = tmp_path / "test_dir"
        directory.mkdir()
        monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

        result = read_file(str(directory))

        assert "Error:" in result
        assert "directory" in result.lower()

    def test_parse_template_with_non_utf8(self):
        """Test parse_template with non-UTF-8 file."""
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".erb", delete=False) as f:
            # Write invalid UTF-8 bytes
            f.write(b"\x80\x81\x82\x83\x84\x85")
            f.flush()
            temp_path = f.name

        try:
            result = parse_template(temp_path)
            # Should handle error gracefully
            assert "Error:" in result or "Unable to decode" in result
        finally:
            Path(temp_path).unlink()

    def test_parse_custom_resource_with_non_utf8(self):
        """Test parse_custom_resource with non-UTF-8 file."""
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".rb", delete=False) as f:
            f.write(b"\x80\x81\x82\x83\x84\x85")
            f.flush()
            temp_path = f.name

        try:
            result = parse_custom_resource(temp_path)
            assert "Error:" in result or "Unable to decode" in result
        finally:
            Path(temp_path).unlink()

    def test_read_file_with_non_utf8(self):
        """Test read_file with non-UTF-8 file."""
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".txt", delete=False) as f:
            f.write(b"\x80\x81\x82\x83\x84\x85")
            f.flush()
            temp_path = f.name

        try:
            result = read_file(temp_path)
            assert "Error:" in result or "Unable to decode" in result
        finally:
            Path(temp_path).unlink()
