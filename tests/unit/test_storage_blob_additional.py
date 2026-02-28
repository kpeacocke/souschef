"""Additional tests for blob storage coverage."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from souschef.storage.blob import LocalBlobStorage, S3BlobStorage, get_blob_storage


def test_local_blob_storage_file_round_trip(tmp_path: Path) -> None:
    """Upload and download a file via local blob storage."""
    storage = LocalBlobStorage(base_path=tmp_path / "storage")

    source = tmp_path / "file.txt"
    source.write_text("content")

    key = storage.upload(source, "file.txt")
    assert key == "file.txt"

    target = tmp_path / "downloaded.txt"
    result = storage.download(key, target)

    assert result.read_text() == "content"
    assert storage.delete(key) is True


def test_local_blob_storage_directory_round_trip(tmp_path: Path) -> None:
    """Upload and download a directory via local blob storage."""
    storage = LocalBlobStorage(base_path=tmp_path / "storage")

    source_dir = tmp_path / "dir"
    source_dir.mkdir()
    (source_dir / "a.txt").write_text("a")

    key = storage.upload(source_dir, "archive")
    assert key.endswith(".zip")

    target_dir = tmp_path / "out"
    storage.download(key, target_dir)

    assert (target_dir / "a.txt").read_text() == "a"


def test_local_blob_storage_list_keys_prefix(tmp_path: Path) -> None:
    """List keys should respect prefix filtering."""
    storage = LocalBlobStorage(base_path=tmp_path / "storage")

    (storage.base_path / "a.txt").write_text("a")
    (storage.base_path / "sub").mkdir()
    (storage.base_path / "sub" / "b.txt").write_text("b")

    keys = storage.list_keys(prefix="sub")

    assert "sub/b.txt" in keys
    assert "a.txt" not in keys


def test_local_blob_storage_missing_key_raises(tmp_path: Path) -> None:
    """Missing storage key should raise FileNotFoundError."""
    storage = LocalBlobStorage(base_path=tmp_path / "storage")

    with pytest.raises(FileNotFoundError):
        storage.download("missing.txt", tmp_path / "out.txt")


def test_s3_blob_storage_import_error() -> None:
    """Missing boto3 should raise ImportError."""
    with (
        patch("importlib.import_module", side_effect=ImportError("no boto3")),
        pytest.raises(ImportError, match="boto3 is required"),
    ):
        S3BlobStorage(bucket_name="test")


def test_get_blob_storage_unknown_backend() -> None:
    """Unknown backend should raise ValueError."""
    # Need to reset the global since it caches
    import souschef.storage.blob as blob_module

    old_storage = blob_module._blob_storage
    try:
        blob_module._blob_storage = None
        with pytest.raises(ValueError, match="Unknown blob storage backend"):
            get_blob_storage(backend="unknown_backend")
    finally:
        blob_module._blob_storage = old_storage
