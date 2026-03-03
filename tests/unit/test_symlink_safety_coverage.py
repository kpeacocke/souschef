"""Test coverage for _check_symlink_safety exception handling."""

from pathlib import Path
from unittest.mock import patch

from souschef.core.path_utils import _check_symlink_safety


def test_check_symlink_safety_filenotfound_exception() -> None:
    """Test _check_symlink_safety handles FileNotFoundError gracefully."""
    path = Path("/workspaces/souschef/nonexistent/path")
    # Mock is_symlink to raise FileNotFoundError
    with patch.object(Path, "is_symlink", side_effect=FileNotFoundError()):
        # Should not raise, should return silently
        _check_symlink_safety(path)


def test_check_symlink_safety_permission_error() -> None:
    """Test _check_symlink_safety handles PermissionError gracefully."""
    path = Path("/workspaces/souschef/restricted/path")
    # Mock is_symlink to raise PermissionError
    with patch.object(Path, "is_symlink", side_effect=PermissionError()):
        # Should not raise, should return silently
        _check_symlink_safety(path)


def test_check_symlink_safety_notadirectory_error() -> None:
    """Test _check_symlink_safety handles NotADirectoryError gracefully."""
    path = Path("/workspaces/souschef/file/as/dir")
    # Mock is_symlink to raise NotADirectoryError
    with patch.object(Path, "is_symlink", side_effect=NotADirectoryError()):
        # Should not raise, should return silently
        _check_symlink_safety(path)
