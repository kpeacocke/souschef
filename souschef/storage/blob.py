"""Blob storage integration for SousChef generated assets."""

import importlib
import io
import os
import shutil
import tempfile
import zipfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from souschef.core.path_utils import _ensure_within_base_path, _normalize_path
from souschef.storage.config import load_blob_settings


class BlobStorage(ABC):
    """Abstract base class for blob storage backends."""

    @abstractmethod
    def upload(self, local_path: Path, storage_key: str) -> str:
        """
        Upload a file or directory to blob storage.

        Args:
            local_path: Path to local file or directory.
            storage_key: Key/path in blob storage.

        Returns:
            Storage key for the uploaded content.

        """
        pass

    @abstractmethod
    def download(self, storage_key: str, local_path: Path) -> Path:
        """
        Download a file from blob storage.

        Args:
            storage_key: Key/path in blob storage.
            local_path: Path to save downloaded content.

        Returns:
            Path to downloaded file.

        """
        pass

    @abstractmethod
    def delete(self, storage_key: str) -> bool:
        """
        Delete a file from blob storage.

        Args:
            storage_key: Key/path in blob storage.

        Returns:
            True if deleted successfully.

        """
        pass

    @abstractmethod
    def list_keys(self, prefix: str = "") -> list[str]:
        """
        List storage keys with optional prefix.

        Args:
            prefix: Optional prefix to filter keys.

        Returns:
            List of storage keys.

        """
        pass


class LocalBlobStorage(BlobStorage):
    """Local filesystem implementation of blob storage."""

    def __init__(self, base_path: str | Path | None = None):
        """
        Initialise local blob storage.

        Args:
            base_path: Base directory for storage. If None, uses default location.

        """
        if base_path is None:
            base_path = self._get_default_storage_path()
        else:
            base_path = _normalize_path(str(base_path))

        self.base_path = base_path
        self.base_path.mkdir(parents=True, exist_ok=True, mode=0o700)

    def _get_default_storage_path(self) -> Path:
        """Get the default storage path."""
        data_dir = Path(tempfile.gettempdir()) / ".souschef" / "storage"
        data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        return _ensure_within_base_path(data_dir, Path(tempfile.gettempdir()))

    def _get_full_path(self, storage_key: str) -> Path:
        """Get full filesystem path for a storage key."""
        # Sanitise the storage key to prevent path traversal
        safe_key = storage_key.replace("..", "_").replace(os.sep, "_")
        full_path = self.base_path / safe_key
        return _ensure_within_base_path(full_path, self.base_path)

    def upload(self, local_path: Path, storage_key: str) -> str:
        """Upload a file or directory to local storage."""
        # Validate local_path is safe
        local_path = _normalize_path(str(local_path))

        dest_path = self._get_full_path(storage_key)

        if local_path.is_dir():
            # Create a ZIP archive of the directory
            zip_path = dest_path.with_suffix(".zip")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for file_path in local_path.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(local_path)
                        zipf.write(file_path, arcname)
            return storage_key + ".zip"
        else:
            # Copy single file
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(local_path, dest_path)
            return storage_key

    def download(self, storage_key: str, local_path: Path) -> Path:
        """Download a file from local storage."""
        source_path = self._get_full_path(storage_key)

        if not source_path.exists():
            raise FileNotFoundError(f"Storage key not found: {storage_key}")

        # Validate local_path is safe
        local_path = _normalize_path(str(local_path))

        if source_path.suffix == ".zip":
            # Extract ZIP archive
            local_path.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(source_path, "r") as zipf:
                zipf.extractall(local_path)
        else:
            # Copy single file
            local_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, local_path)

        return local_path

    def delete(self, storage_key: str) -> bool:
        """Delete a file from local storage."""
        try:
            path = self._get_full_path(storage_key)
            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
                return True
        except OSError:
            pass
        return False

    def list_keys(self, prefix: str = "") -> list[str]:
        """List storage keys with optional prefix."""
        keys = []
        for path in self.base_path.rglob("*"):
            if path.is_file():
                relative = path.relative_to(self.base_path)
                key = str(relative)
                if not prefix or key.startswith(prefix):
                    keys.append(key)
        return sorted(keys)


class S3BlobStorage(BlobStorage):
    """S3-compatible blob storage implementation."""

    def __init__(
        self,
        bucket_name: str,
        access_key: str | None = None,
        secret_key: str | None = None,
        endpoint_url: str | None = None,
        region: str = "us-east-1",
    ):
        """
        Initialise S3 blob storage.

        Args:
            bucket_name: S3 bucket name.
            access_key: AWS access key (or from environment).
            secret_key: AWS secret key (or from environment).
            endpoint_url: Custom endpoint URL (for MinIO/LocalStack).
            region: AWS region.

        """
        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url
        self.region = region

        # Try to import boto3
        try:
            boto3 = importlib.import_module("boto3")
        except ImportError as exc:
            raise ImportError(
                "boto3 is required for S3 storage. Install with: pip install boto3"
            ) from exc

        # Configure client
        config_kwargs: dict[str, Any] = {}
        if access_key and secret_key:
            config_kwargs["aws_access_key_id"] = access_key
            config_kwargs["aws_secret_access_key"] = secret_key
        if endpoint_url:
            config_kwargs["endpoint_url"] = endpoint_url

        self.s3 = boto3.client("s3", region_name=region, **config_kwargs)

        # Ensure bucket exists
        try:
            self.s3.head_bucket(Bucket=bucket_name)
        except Exception:
            self.s3.create_bucket(Bucket=bucket_name)

    def upload(self, local_path: Path, storage_key: str) -> str:
        """Upload a file or directory to S3."""
        # Validate local_path is safe
        local_path = _normalize_path(str(local_path))

        if local_path.is_dir():
            # Create a ZIP archive
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
                for file_path in local_path.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(local_path)
                        zipf.write(file_path, arcname)

            zip_buffer.seek(0)
            storage_key = storage_key + ".zip"
            self.s3.upload_fileobj(zip_buffer, self.bucket_name, storage_key)
        else:
            # Upload single file
            with local_path.open("rb") as f:
                self.s3.upload_fileobj(f, self.bucket_name, storage_key)

        return storage_key

    def download(self, storage_key: str, local_path: Path) -> Path:
        """Download a file from S3."""
        # Validate local_path is safe
        local_path = _normalize_path(str(local_path))

        if storage_key.endswith(".zip"):
            # Download and extract ZIP
            zip_buffer = io.BytesIO()
            self.s3.download_fileobj(self.bucket_name, storage_key, zip_buffer)
            zip_buffer.seek(0)

            local_path.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(zip_buffer, "r") as zipf:
                zipf.extractall(local_path)
        else:
            # Download single file
            local_path.parent.mkdir(parents=True, exist_ok=True)
            with local_path.open("wb") as f:
                self.s3.download_fileobj(self.bucket_name, storage_key, f)

        return local_path

    def delete(self, storage_key: str) -> bool:
        """Delete a file from S3."""
        try:
            self.s3.delete_object(Bucket=self.bucket_name, Key=storage_key)
            return True
        except Exception:
            return False

    def list_keys(self, prefix: str = "") -> list[str]:
        """List storage keys with optional prefix."""
        try:
            response = self.s3.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
            return [obj["Key"] for obj in response.get("Contents", [])]
        except Exception:
            return []


# Singleton instance
_blob_storage: BlobStorage | None = None


def get_blob_storage(backend: str | None = None, **config: Any) -> BlobStorage:
    """
    Get or create the blob storage instance.

    Args:
        backend: Storage backend ('local', 's3', 'minio').
        **config: Configuration options for the backend.

    Returns:
        BlobStorage instance.

    """
    global _blob_storage

    settings = load_blob_settings()
    resolved_backend = backend or settings.backend

    if _blob_storage is None:
        if resolved_backend == "local":
            _blob_storage = LocalBlobStorage(config.get("base_path"))
        elif resolved_backend in ["s3", "minio"]:
            _blob_storage = S3BlobStorage(
                bucket_name=config.get("bucket_name", settings.s3_bucket),
                access_key=config.get("access_key", settings.s3_access_key),
                secret_key=config.get("secret_key", settings.s3_secret_key),
                endpoint_url=config.get("endpoint_url", settings.s3_endpoint),
                region=config.get("region", settings.s3_region),
            )
        else:
            raise ValueError(f"Unknown blob storage backend: {resolved_backend}")

    return _blob_storage
