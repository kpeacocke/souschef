"""Tests for the SousChef MCP server."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from souschef.server import list_directory


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
