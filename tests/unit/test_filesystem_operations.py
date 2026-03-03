"""Tests for filesystem operations error handling."""

from pathlib import Path

import pytest

from souschef.filesystem.operations import create_tar_gz_archive, list_directory


def test_list_directory_invalid_path_returns_error() -> None:
    """Test list_directory returns error on invalid path input."""
    result = list_directory("invalid\x00path")

    assert isinstance(result, str)
    assert result.startswith("Error:")


def test_create_tar_gz_archive_with_non_directory(tmp_path: Path) -> None:
    """Test archive creation rejects non-directory sources."""
    source_file = tmp_path / "source.txt"
    source_file.write_text("content")
    output_file = tmp_path / "out.tar.gz"

    with pytest.raises(ValueError, match="Source directory does not exist"):
        create_tar_gz_archive(str(source_file), str(output_file))
