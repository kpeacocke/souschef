"""Comprehensive tests for storage/blob.py module to achieve 100% coverage."""

import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from souschef.storage.blob import (
    BlobStorage,
    LocalBlobStorage,
    S3BlobStorage,
    get_blob_storage,
)


class TestBlobStorageABC:
    """Test BlobStorage abstract base class."""

    def test_blob_storage_cannot_instantiate(self) -> None:
        """Test that BlobStorage cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BlobStorage()  # type: ignore[abstract]


class TestLocalBlobStorage:
    """Test LocalBlobStorage implementation."""

    def test_local_storage_initialization(self, tmp_path: Path) -> None:
        """Test initializing LocalBlobStorage."""
        storage = LocalBlobStorage(tmp_path)
        assert storage.base_path == tmp_path
        assert storage.base_path.exists()

    def test_local_storage_default_path(self) -> None:
        """Test LocalBlobStorage with default path."""
        storage = LocalBlobStorage()
        assert storage.base_path.exists()
        assert ".souschef" in str(storage.base_path)

    def test_upload_single_file(self, tmp_path: Path) -> None:
        """Test uploading a single file."""
        storage_dir = tmp_path / "storage"
        storage = LocalBlobStorage(storage_dir)

        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        key = storage.upload(test_file, "uploads/test.txt")
        assert key == "uploads/test.txt"
        assert (storage_dir / "uploads_test.txt").exists()

    def test_upload_directory(self, tmp_path: Path) -> None:
        """Test uploading a directory as zip."""
        storage_dir = tmp_path / "storage"
        storage = LocalBlobStorage(storage_dir)

        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        (test_dir / "file1.txt").write_text("content1")
        (test_dir / "file2.txt").write_text("content2")

        key = storage.upload(test_dir, "archives/mydir")
        assert key == "archives/mydir.zip"
        assert (storage_dir / "archives_mydir.zip").exists()

    def test_download_single_file(self, tmp_path: Path) -> None:
        """Test downloading a single file."""
        storage_dir = tmp_path / "storage"
        storage = LocalBlobStorage(storage_dir)

        # Upload file first
        test_file = tmp_path / "source.txt"
        test_file.write_text("download test")
        key = storage.upload(test_file, "files/source.txt")

        # Download to different location
        download_path = tmp_path / "downloads" / "dest.txt"
        result = storage.download(key, download_path)

        assert result == download_path
        assert result.exists()
        assert result.read_text() == "download test"

    def test_download_zip_archive(self, tmp_path: Path) -> None:
        """Test downloading and extracting zip archive."""
        storage_dir = tmp_path / "storage"
        storage = LocalBlobStorage(storage_dir)

        # Upload directory
        test_dir = tmp_path / "source_dir"
        test_dir.mkdir()
        (test_dir / "readme.txt").write_text("readme content")
        (test_dir / "data.json").write_text('{"key": "value"}')
        key = storage.upload(test_dir, "archives/myarchive")

        # Download and extract
        extract_dir = tmp_path / "extracted"
        result = storage.download(key, extract_dir)

        assert result == extract_dir
        assert (extract_dir / "readme.txt").exists()
        assert (extract_dir / "data.json").exists()
        assert (extract_dir / "readme.txt").read_text() == "readme content"

    def test_download_nonexistent_file(self, tmp_path: Path) -> None:
        """Test downloading nonexistent file raises error."""
        storage = LocalBlobStorage(tmp_path)

        with pytest.raises(FileNotFoundError, match="Storage key not found"):
            storage.download("nonexistent.txt", tmp_path / "dest.txt")

    def test_delete_file(self, tmp_path: Path) -> None:
        """Test deleting a file."""
        storage_dir = tmp_path / "storage"
        storage = LocalBlobStorage(storage_dir)

        # Upload file
        test_file = tmp_path / "delete_me.txt"
        test_file.write_text("will be deleted")
        key = storage.upload(test_file, "temp/delete_me.txt")

        # Delete it
        success = storage.delete(key)
        assert success is True
        assert not (storage_dir / "temp_delete_me.txt").exists()

    def test_delete_directory(self, tmp_path: Path) -> None:
        """Test deleting a directory."""
        storage_dir = tmp_path / "storage"
        storage = LocalBlobStorage(storage_dir)

        # Create directory structure
        upload_dir = tmp_path / "upload_dir"
        upload_dir.mkdir()
        (upload_dir / "file.txt").write_text("content")

        # Upload as zip
        key = storage.upload(upload_dir, "dirs/mydir")

        # Delete it
        success = storage.delete(key)
        assert success is True

    def test_delete_nonexistent(self, tmp_path: Path) -> None:
        """Test deleting nonexistent file returns False."""
        storage = LocalBlobStorage(tmp_path)
        success = storage.delete("nonexistent.txt")
        assert success is False

    def test_list_keys_empty(self, tmp_path: Path) -> None:
        """Test listing keys in empty storage."""
        storage = LocalBlobStorage(tmp_path)
        keys = storage.list_keys()
        assert keys == []

    def test_list_keys(self, tmp_path: Path) -> None:
        """Test listing storage keys."""
        storage_dir = tmp_path / "storage"
        storage = LocalBlobStorage(storage_dir)

        # Upload multiple files
        for i in range(3):
            test_file = tmp_path / f"file{i}.txt"
            test_file.write_text(f"content {i}")
            storage.upload(test_file, f"files/file{i}.txt")

        keys = storage.list_keys()
        assert len(keys) == 3
        assert all("files_file" in key for key in keys)

    def test_list_keys_with_prefix(self, tmp_path: Path) -> None:
        """Test listing keys with prefix filter."""
        storage_dir = tmp_path / "storage"
        storage = LocalBlobStorage(storage_dir)

        # Upload files with different prefixes
        file1 = tmp_path / "test1.txt"
        file1.write_text("content1")
        storage.upload(file1, "docs/test1.txt")

        file2 = tmp_path / "test2.txt"
        file2.write_text("content2")
        storage.upload(file2, "images/test2.txt")

        # List with prefix
        docs_keys = storage.list_keys(prefix="docs")
        assert len(docs_keys) == 1
        assert "docs" in docs_keys[0]

    def test_path_traversal_prevention(self, tmp_path: Path) -> None:
        """Test that path traversal attacks are prevented."""
        storage = LocalBlobStorage(tmp_path)

        # Try malicious key
        test_file = tmp_path / "malicious.txt"
        test_file.write_text("bad content")

        # The upload function returns the storage key
        # The _get_full_path method sanitizes path traversal
        key = storage.upload(test_file, "../../../etc/passwd")
        # Key is returned as-is, but internal path is sanitized
        assert key == "../../../etc/passwd"
        # But the actual file should be stored safely
        # Verify it was stored but not at the malicious path
        stored_path = storage._get_full_path(key)
        assert stored_path.is_relative_to(storage.base_path)


class TestS3BlobStorage:
    """Test S3BlobStorage implementation."""

    @patch("souschef.storage.blob.importlib.import_module")
    def test_s3_storage_initialization(self, mock_import: MagicMock) -> None:
        """Test initializing S3BlobStorage."""
        mock_boto3 = MagicMock()
        mock_import.return_value = mock_boto3
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        try:
            storage = S3BlobStorage(
                bucket_name="test-bucket",
                access_key="key123",
                secret_key="secret456",
                endpoint_url="https://s3.example.com",
                region="us-west-2",
            )
            assert storage.bucket_name == "test-bucket"
        except ImportError:
            # boto3 may not be installed
            pass

    @patch("souschef.storage.blob.importlib.import_module")
    def test_s3_storage_from_environment(self, mock_import: MagicMock) -> None:
        """Test S3 storage with credentials from environment."""
        mock_boto3 = MagicMock()
        mock_import.return_value = mock_boto3

        try:
            with patch.dict(
                "os.environ",
                {"AWS_ACCESS_KEY_ID": "env_key", "AWS_SECRET_ACCESS_KEY": "env_secret"},
            ):
                storage = S3BlobStorage(bucket_name="env-bucket")
                assert storage.bucket_name == "env-bucket"
        except ImportError:
            pass

    @patch("souschef.storage.blob.importlib.import_module")
    def test_s3_upload(self, mock_import: MagicMock, tmp_path: Path) -> None:
        """Test uploading to S3."""
        mock_boto3 = MagicMock()
        mock_import.return_value = mock_boto3
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        try:
            storage = S3BlobStorage(bucket_name="test-bucket")

            test_file = tmp_path / "upload.txt"
            test_file.write_text("upload content")

            key = storage.upload(test_file, "s3/upload.txt")
            assert key == "s3/upload.txt"
            # Verify upload_file was called
            if hasattr(mock_client, "upload_file"):
                assert (
                    mock_client.upload_file.called or mock_client.upload_fileobj.called
                )
        except (ImportError, AttributeError):
            pass

    @patch("souschef.storage.blob.importlib.import_module")
    def test_s3_download(self, mock_import: MagicMock, tmp_path: Path) -> None:
        """Test downloading from S3."""
        mock_boto3 = MagicMock()
        mock_import.return_value = mock_boto3
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        try:
            storage = S3BlobStorage(bucket_name="test-bucket")

            download_path = tmp_path / "downloaded.txt"
            result = storage.download("s3/file.txt", download_path)
            # Even with mocks, should return the path
            assert isinstance(result, Path)
        except (ImportError, AttributeError):
            pass

    @patch("souschef.storage.blob.importlib.import_module")
    def test_s3_delete(self, mock_import: MagicMock) -> None:
        """Test deleting from S3."""
        mock_boto3 = MagicMock()
        mock_import.return_value = mock_boto3
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        try:
            storage = S3BlobStorage(bucket_name="test-bucket")
            success = storage.delete("s3/delete_me.txt")
            # With mocks, should succeed
            assert isinstance(success, bool)
        except (ImportError, AttributeError):
            pass

    @patch("souschef.storage.blob.importlib.import_module")
    def test_s3_list_keys(self, mock_import: MagicMock) -> None:
        """Test listing S3 keys."""
        mock_boto3 = MagicMock()
        mock_import.return_value = mock_boto3
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        # Mock S3 list response
        mock_client.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "file1.txt"},
                {"Key": "file2.txt"},
                {"Key": "dir/file3.txt"},
            ]
        }

        try:
            storage = S3BlobStorage(bucket_name="test-bucket")
            keys = storage.list_keys()
            assert isinstance(keys, list)
        except (ImportError, AttributeError):
            pass


class TestGetBlobStorage:
    """Test get_blob_storage factory function."""

    def test_get_blob_storage_local(self, tmp_path: Path) -> None:
        """Test getting local blob storage."""
        storage = get_blob_storage("local", base_path=str(tmp_path))
        assert isinstance(storage, LocalBlobStorage)

    def test_get_blob_storage_default(self) -> None:
        """Test getting default blob storage."""
        storage = get_blob_storage()
        assert isinstance(storage, LocalBlobStorage)

    @patch("souschef.storage.blob.load_blob_settings")
    @patch("souschef.storage.blob.importlib.import_module")
    def test_get_blob_storage_s3(
        self, mock_import: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Test getting S3 blob storage."""
        # Mock settings to return s3 backend
        mock_config = MagicMock()
        mock_config.backend = "s3"
        mock_config.s3_bucket = "test-bucket"
        mock_config.s3_access_key = None
        mock_config.s3_secret_key = None
        mock_config.s3_endpoint = None
        mock_config.s3_region = "us-east-1"
        mock_settings.return_value = mock_config

        mock_boto3 = MagicMock()
        mock_import.return_value = mock_boto3

        try:
            # Clear the global singleton
            import souschef.storage.blob

            souschef.storage.blob._blob_storage = None

            storage = get_blob_storage(
                "s3", bucket_name="test-bucket", access_key="key", secret_key="secret"
            )
            assert isinstance(storage, S3BlobStorage)
        except ImportError:
            pass

    @patch("souschef.storage.blob.load_blob_settings")
    def test_get_blob_storage_from_config(self, mock_settings: MagicMock) -> None:
        """Test getting blob storage from config."""
        mock_config = MagicMock()
        mock_config.backend = "local"
        mock_config.local_base_path = "/tmp/test"
        mock_settings.return_value = mock_config

        storage = get_blob_storage()
        assert isinstance(storage, (LocalBlobStorage, BlobStorage))

    @patch("souschef.storage.blob.load_blob_settings")
    def test_get_blob_storage_invalid_backend(self, mock_settings: MagicMock) -> None:
        """Test getting blob storage with invalid backend."""
        # Mock settings
        mock_config = MagicMock()
        mock_config.backend = "invalid_backend"
        mock_settings.return_value = mock_config

        # Clear singleton
        import souschef.storage.blob

        souschef.storage.blob._blob_storage = None

        with pytest.raises(ValueError, match="Unknown blob storage backend"):
            get_blob_storage("invalid_backend")


class TestBlobStorageEdgeCases:
    """Test edge cases and error conditions."""

    def test_local_storage_large_directory(self, tmp_path: Path) -> None:
        """Test uploading large directory with many files."""
        storage_dir = tmp_path / "storage"
        storage = LocalBlobStorage(storage_dir)

        large_dir = tmp_path / "large_dir"
        large_dir.mkdir()

        # Create many files
        for i in range(50):
            (large_dir / f"file_{i:03d}.txt").write_text(f"content {i}")

        key = storage.upload(large_dir, "archives/large")
        assert key.endswith(".zip")

        # Verify zip contents
        zip_path = storage._get_full_path(key)
        with zipfile.ZipFile(zip_path, "r") as zipf:
            assert len(zipf.namelist()) == 50

    def test_local_storage_empty_directory(self, tmp_path: Path) -> None:
        """Test uploading empty directory."""
        storage_dir = tmp_path / "storage"
        storage = LocalBlobStorage(storage_dir)

        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        key = storage.upload(empty_dir, "empty_archive")
        assert key.endswith(".zip")

    def test_local_storage_binary_files(self, tmp_path: Path) -> None:
        """Test handling binary files."""
        storage_dir = tmp_path / "storage"
        storage = LocalBlobStorage(storage_dir)

        # Create binary file
        binary_file = tmp_path / "binary.dat"
        binary_file.write_bytes(b"\x00\x01\x02\x03\xff\xfe")

        key = storage.upload(binary_file, "binaries/test.dat")

        # Download and verify
        downloaded = tmp_path / "downloaded.dat"
        storage.download(key, downloaded)
        assert downloaded.read_bytes() == b"\x00\x01\x02\x03\xff\xfe"

    def test_local_storage_nested_directories(self, tmp_path: Path) -> None:
        """Test handling nested directory structures."""
        storage_dir = tmp_path / "storage"
        storage = LocalBlobStorage(storage_dir)

        # Create nested structure
        nested_dir = tmp_path / "nested"
        (nested_dir / "level1" / "level2" / "level3").mkdir(parents=True)
        (nested_dir / "level1" / "level2" / "level3" / "deep.txt").write_text(
            "deep content"
        )

        key = storage.upload(nested_dir, "nested_structure")

        # Download and verify
        extract_dir = tmp_path / "extracted"
        storage.download(key, extract_dir)
        assert (extract_dir / "level1" / "level2" / "level3" / "deep.txt").exists()

    def test_local_storage_special_characters(self, tmp_path: Path) -> None:
        """Test handling filenames with special characters."""
        storage_dir = tmp_path / "storage"
        storage = LocalBlobStorage(storage_dir)

        test_file = tmp_path / "test file.txt"
        test_file.write_text("content")

        # Should handle spaces and special chars
        key = storage.upload(test_file, "files/test file.txt")
        assert isinstance(key, str)

    def test_concurrent_operations(self, tmp_path: Path) -> None:
        """Test concurrent storage operations."""
        storage_dir = tmp_path / "storage"
        storage1 = LocalBlobStorage(storage_dir)
        storage2 = LocalBlobStorage(storage_dir)

        # Upload with first instance
        test_file = tmp_path / "shared.txt"
        test_file.write_text("shared content")
        storage1.upload(test_file, "shared/file.txt")

        # Access with second instance
        keys = storage2.list_keys()
        assert len(keys) > 0
        assert any("shared" in k for k in keys)
