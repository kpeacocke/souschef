"""Tests for the SousChef MCP server."""

import os
from unittest.mock import patch

from souschef.server import list_directory


def test_list_directory_success():
    """Test that list_directory returns a list of files."""
    with patch("os.listdir") as mock_listdir:
        mock_listdir.return_value = ["file1.txt", "file2.txt"]
        result = list_directory(".")
        assert result == ["file1.txt", "file2.txt"]


def test_list_directory_not_found():
    """Test that list_directory returns an error when the directory is not found."""
    with patch("os.listdir") as mock_listdir:
        mock_listdir.side_effect = FileNotFoundError
        result = list_directory("non_existent_directory")
        assert "Error: Directory not found" in result


def test_list_directory_permission_denied():
    """Test that list_directory returns an error on permission denied."""
    with patch("os.listdir") as mock_listdir:
        mock_listdir.side_effect = PermissionError
        result = list_directory("/root")
        assert "Error: Permission denied" in result


def test_list_directory_other_exception():
    """Test that list_directory returns an error on other exceptions."""
    with patch("os.listdir") as mock_listdir:
        mock_listdir.side_effect = Exception("A test exception")
        result = list_directory(".")
        assert "An error occurred: A test exception" in result
