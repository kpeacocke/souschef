"""Tests for the SousChef MCP server."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from souschef.server import (
    list_directory,
    read_cookbook_metadata,
    read_file,
)


def test_list_directory_success():
    """Test that list_directory returns a list of files."""
    mock_path = MagicMock(spec=Path)
    mock_file1 = MagicMock()
    mock_file1.name = "file1.txt"
    mock_file2 = MagicMock()
    mock_file2.name = "file2.txt"
    mock_path.iterdir.return_value = [mock_file1, mock_file2]

    with patch("souschef.server.Path", return_value=mock_path):
        result = list_directory(".")
        assert result == ["file1.txt", "file2.txt"]


def test_list_directory_empty():
    """Test that list_directory returns an empty list for empty directories."""
    mock_path = MagicMock(spec=Path)
    mock_path.iterdir.return_value = []

    with patch("souschef.server.Path", return_value=mock_path):
        result = list_directory("/empty")
        assert result == []


def test_list_directory_not_found():
    """Test that list_directory returns an error when directory not found."""
    mock_path = MagicMock(spec=Path)
    mock_path.iterdir.side_effect = FileNotFoundError

    with patch("souschef.server.Path", return_value=mock_path):
        result = list_directory("non_existent_directory")
        assert "Error: Directory not found" in result


def test_list_directory_not_a_directory():
    """Test that list_directory returns an error when path is a file."""
    mock_path = MagicMock(spec=Path)
    mock_path.iterdir.side_effect = NotADirectoryError

    with patch("souschef.server.Path", return_value=mock_path):
        result = list_directory("file.txt")
        assert "Error:" in result
        assert "is not a directory" in result


def test_list_directory_permission_denied():
    """Test that list_directory returns an error on permission denied."""
    mock_path = MagicMock(spec=Path)
    mock_path.iterdir.side_effect = PermissionError

    with patch("souschef.server.Path", return_value=mock_path):
        result = list_directory("/root")
        assert "Error: Permission denied" in result


def test_list_directory_other_exception():
    """Test that list_directory returns an error on other exceptions."""
    mock_path = MagicMock(spec=Path)
    mock_path.iterdir.side_effect = Exception("A test exception")

    with patch("souschef.server.Path", return_value=mock_path):
        result = list_directory(".")
        assert "An error occurred: A test exception" in result


def test_read_file_success():
    """Test that read_file returns the file contents."""
    mock_path = MagicMock(spec=Path)
    mock_path.read_text.return_value = "file contents here"

    with patch("souschef.server.Path", return_value=mock_path):
        result = read_file("test.txt")
        assert result == "file contents here"
        mock_path.read_text.assert_called_once_with(encoding="utf-8")


def test_read_file_not_found():
    """Test that read_file returns an error when file not found."""
    mock_path = MagicMock(spec=Path)
    mock_path.read_text.side_effect = FileNotFoundError

    with patch("souschef.server.Path", return_value=mock_path):
        result = read_file("missing.txt")
        assert "Error: File not found" in result


def test_read_file_is_directory():
    """Test that read_file returns an error when path is a directory."""
    mock_path = MagicMock(spec=Path)
    mock_path.read_text.side_effect = IsADirectoryError

    with patch("souschef.server.Path", return_value=mock_path):
        result = read_file("somedir")
        assert "Error:" in result
        assert "is a directory" in result


def test_read_file_permission_denied():
    """Test that read_file returns an error on permission denied."""
    mock_path = MagicMock(spec=Path)
    mock_path.read_text.side_effect = PermissionError

    with patch("souschef.server.Path", return_value=mock_path):
        result = read_file("protected.txt")
        assert "Error: Permission denied" in result


def test_read_file_unicode_decode_error():
    """Test that read_file returns an error on unicode decode failure."""
    mock_path = MagicMock(spec=Path)
    mock_path.read_text.side_effect = UnicodeDecodeError(
        "utf-8", b"", 0, 1, "invalid"
    )

    with patch("souschef.server.Path", return_value=mock_path):
        result = read_file("binary.dat")
        assert "Error: Unable to decode" in result
        assert "UTF-8" in result


def test_read_file_other_exception():
    """Test that read_file returns an error on other exceptions."""
    mock_path = MagicMock(spec=Path)
    mock_path.read_text.side_effect = Exception("Unexpected error")

    with patch("souschef.server.Path", return_value=mock_path):
        result = read_file("test.txt")
        assert "An error occurred: Unexpected error" in result


def test_read_cookbook_metadata_success():
    """Test read_cookbook_metadata with valid metadata.rb."""
    metadata_content = """
name 'apache2'
maintainer 'Chef Software, Inc.'
version '8.0.0'
description 'Installs and configures Apache'
license 'Apache-2.0'
depends 'logrotate'
depends 'iptables'
supports 'ubuntu'
supports 'debian'
    """
    with patch("souschef.server.Path") as mock_path:
        mock_instance = MagicMock()
        mock_path.return_value = mock_instance
        mock_instance.read_text.return_value = metadata_content

        result = read_cookbook_metadata("/cookbook/metadata.rb")

        assert "name: apache2" in result
        assert "maintainer: Chef Software, Inc." in result
        assert "version: 8.0.0" in result
        assert "description: Installs and configures Apache" in result
        assert "license: Apache-2.0" in result
        assert "depends: logrotate, iptables" in result
        assert "supports: ubuntu, debian" in result


def test_read_cookbook_metadata_minimal():
    """Test read_cookbook_metadata with minimal metadata."""
    metadata_content = "name 'simple'"
    with patch("souschef.server.Path") as mock_path:
        mock_instance = MagicMock()
        mock_path.return_value = mock_instance
        mock_instance.read_text.return_value = metadata_content

        result = read_cookbook_metadata("/cookbook/metadata.rb")

        assert "name: simple" in result
        assert "depends" not in result


def test_read_cookbook_metadata_empty():
    """Test read_cookbook_metadata with empty file."""
    with patch("souschef.server.Path") as mock_path:
        mock_instance = MagicMock()
        mock_path.return_value = mock_instance
        mock_instance.read_text.return_value = ""

        result = read_cookbook_metadata("/cookbook/metadata.rb")

        assert "Warning: No metadata found" in result


def test_read_cookbook_metadata_not_found():
    """Test read_cookbook_metadata with non-existent file."""
    with patch("souschef.server.Path") as mock_path:
        mock_instance = MagicMock()
        mock_path.return_value = mock_instance
        mock_instance.read_text.side_effect = FileNotFoundError()

        result = read_cookbook_metadata("/nonexistent/metadata.rb")

        assert "Error: File not found" in result


def test_read_cookbook_metadata_is_directory():
    """Test read_cookbook_metadata when path is a directory."""
    with patch("souschef.server.Path") as mock_path:
        mock_instance = MagicMock()
        mock_path.return_value = mock_instance
        mock_instance.read_text.side_effect = IsADirectoryError()

        result = read_cookbook_metadata("/some/directory")

        assert "Error:" in result
        assert "is a directory" in result


def test_read_cookbook_metadata_permission_denied():
    """Test read_cookbook_metadata with permission error."""
    with patch("souschef.server.Path") as mock_path:
        mock_instance = MagicMock()
        mock_path.return_value = mock_instance
        mock_instance.read_text.side_effect = PermissionError()

        result = read_cookbook_metadata("/forbidden/metadata.rb")

        assert "Error: Permission denied" in result


def test_read_cookbook_metadata_unicode_error():
    """Test read_cookbook_metadata with unicode decode error."""
    with patch("souschef.server.Path") as mock_path:
        mock_instance = MagicMock()
        mock_path.return_value = mock_instance
        mock_instance.read_text.side_effect = UnicodeDecodeError(
            "utf-8", b"", 0, 1, "invalid"
        )

        result = read_cookbook_metadata("/binary/file")

        assert "Error: Unable to decode" in result
        assert "UTF-8" in result


def test_read_cookbook_metadata_other_exception():
    """Test read_cookbook_metadata with unexpected exception."""
    with patch("souschef.server.Path") as mock_path:
        mock_instance = MagicMock()
        mock_path.return_value = mock_instance
        mock_instance.read_text.side_effect = Exception("Unexpected")

        result = read_cookbook_metadata("/some/path/metadata.rb")

        assert "An error occurred: Unexpected" in result
