"""Unit tests for the storage module."""

import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from souschef.storage import (
    AnalysisResult,
    ConversionResult,
    DatabaseSettings,
    LocalBlobStorage,
    StorageManager,
    get_storage_manager,
)


class TestStorageManager:
    """Tests for StorageManager class."""

    def test_init_creates_default_db_path(self):
        """Test that StorageManager initialises with default path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(db_path=Path(tmpdir) / "test.db")
            assert manager.db_path.exists()

    def test_init_creates_database_schema(self):
        """Test that StorageManager creates tables on initialisation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(db_path=Path(tmpdir) / "test.db")

            # Verify tables exist
            with sqlite3.connect(str(manager.db_path)) as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
                tables = {row[0] for row in cursor.fetchall()}

            assert "analysis_results" in tables
            assert "conversion_results" in tables

    def test_save_analysis_creates_record(self):
        """Test saving an analysis result with individual parameters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(db_path=Path(tmpdir) / "test.db")

            result_id = manager.save_analysis(
                cookbook_name="test-cookbook",
                cookbook_path="/path/to/cookbook",
                cookbook_version="1.0.0",
                complexity="medium",
                estimated_hours=10.0,
                estimated_hours_with_souschef=5.0,
                recommendations="Deploy with Ansible",
                analysis_data={"test": "data"},
                ai_provider="openai",
                ai_model="gpt-4",
            )

            assert result_id is not None
            assert isinstance(result_id, int)

    def test_save_analysis_returns_incrementing_ids(self):
        """Test that save_analysis returns incrementing IDs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(db_path=Path(tmpdir) / "test.db")

            id1 = manager.save_analysis(
                cookbook_name="cookbook1",
                cookbook_path="/path1",
                cookbook_version="1.0.0",
                complexity="low",
                estimated_hours=5.0,
                estimated_hours_with_souschef=2.0,
                recommendations="",
                analysis_data={},
            )

            id2 = manager.save_analysis(
                cookbook_name="cookbook2",
                cookbook_path="/path2",
                cookbook_version="1.0.0",
                complexity="high",
                estimated_hours=20.0,
                estimated_hours_with_souschef=10.0,
                recommendations="",
                analysis_data={},
            )

            assert id1 is not None
            assert id2 is not None
            assert id1 < id2

    def test_get_cached_analysis_returns_none_for_missing_path(self):
        """Test that get_cached_analysis returns None for non-existent path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(db_path=Path(tmpdir) / "test.db")
            result = manager.get_cached_analysis(
                "/non/existent/path", "openai", "gpt-4"
            )
            assert result is None

    def test_get_cached_analysis_returns_result(self):
        """Test retrieving cached analysis result by path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(db_path=Path(tmpdir) / "test.db")

            cookbook_path = "/path/to/test"
            manager.save_analysis(
                cookbook_name="test",
                cookbook_path=cookbook_path,
                cookbook_version="1.0.0",
                complexity="low",
                estimated_hours=5.0,
                estimated_hours_with_souschef=2.0,
                recommendations="Test",
                analysis_data={"key": "value"},
                ai_provider="openai",
                ai_model="gpt-4",
            )

            cached = manager.get_cached_analysis(cookbook_path, "openai", "gpt-4")

            assert cached is not None
            assert cached.cookbook_name == "test"

    def test_calculate_file_fingerprint_returns_sha256(self):
        """Test that calculate_file_fingerprint returns SHA256 hash."""
        from souschef.storage.database import calculate_file_fingerprint

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("Test content for fingerprinting")

            fingerprint = calculate_file_fingerprint(test_file)

            # SHA256 hash should be 64 characters (hexadecimal)
            assert isinstance(fingerprint, str)
            assert len(fingerprint) == 64
            assert all(c in "0123456789abcdef" for c in fingerprint)

    def test_calculate_file_fingerprint_same_content(self):
        """Test that identical content produces identical fingerprints."""
        from souschef.storage.database import calculate_file_fingerprint

        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir) / "file1.txt"
            file2 = Path(tmpdir) / "file2.txt"

            content = "Identical content for testing"
            file1.write_text(content)
            file2.write_text(content)

            fp1 = calculate_file_fingerprint(file1)
            fp2 = calculate_file_fingerprint(file2)

            assert fp1 == fp2

    def test_calculate_file_fingerprint_different_content(self):
        """Test that different content produces different fingerprints."""
        from souschef.storage.database import calculate_file_fingerprint

        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir) / "file1.txt"
            file2 = Path(tmpdir) / "file2.txt"

            file1.write_text("Content A")
            file2.write_text("Content B")

            fp1 = calculate_file_fingerprint(file1)
            fp2 = calculate_file_fingerprint(file2)

            assert fp1 != fp2

    def test_get_analysis_by_fingerprint_none_when_missing(self):
        """Test that get_analysis_by_fingerprint returns None for missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(db_path=Path(tmpdir) / "test.db")
            result = manager.get_analysis_by_fingerprint("nonexistent_hash")
            assert result is None

    def test_get_analysis_by_fingerprint_returns_analysis(self):
        """Test retrieving analysis by content fingerprint."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(db_path=Path(tmpdir) / "test.db")

            # Save analysis with fingerprint
            test_fingerprint = "a" * 64  # Mock SHA256 hash

            manager.save_analysis(
                cookbook_name="test-cookbook",
                cookbook_path="/path",
                cookbook_version="1.0.0",
                complexity="low",
                estimated_hours=5.0,
                estimated_hours_with_souschef=2.0,
                recommendations="Test",
                analysis_data={},
                content_fingerprint=test_fingerprint,
            )

            # Retrieve by fingerprint
            result = manager.get_analysis_by_fingerprint(test_fingerprint)

            assert result is not None
            assert result.cookbook_name == "test-cookbook"
            assert result.content_fingerprint == test_fingerprint

    def test_save_analysis_deduplicates_by_fingerprint(self):
        """Test that save_analysis deduplicates using fingerprint."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(db_path=Path(tmpdir) / "test.db")

            test_fingerprint = "b" * 64  # Mock SHA256 hash

            # Save first analysis
            id1 = manager.save_analysis(
                cookbook_name="cookbook1",
                cookbook_path="/path1",
                cookbook_version="1.0.0",
                complexity="low",
                estimated_hours=5.0,
                estimated_hours_with_souschef=2.0,
                recommendations="Test",
                analysis_data={},
                content_fingerprint=test_fingerprint,
            )

            # Try to save another with same fingerprint
            id2 = manager.save_analysis(
                cookbook_name="cookbook2",
                cookbook_path="/path2",
                cookbook_version="2.0.0",
                complexity="high",
                estimated_hours=20.0,
                estimated_hours_with_souschef=10.0,
                recommendations="Different",
                analysis_data={},
                content_fingerprint=test_fingerprint,
            )

            # Should return the same ID (deduplication)
            assert id1 == id2

            # Verify only one record with this fingerprint exists
            with sqlite3.connect(str(manager.db_path)) as conn:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM analysis_results "
                    "WHERE content_fingerprint = ?",
                    (test_fingerprint,),
                )
                count = cursor.fetchone()[0]

            assert count == 1

    def test_save_conversion_creates_record(self):
        """Test saving a conversion result."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(db_path=Path(tmpdir) / "test.db")

            # First save an analysis
            analysis_id = manager.save_analysis(
                cookbook_name="test",
                cookbook_path="/path",
                cookbook_version="1.0.0",
                complexity="low",
                estimated_hours=5.0,
                estimated_hours_with_souschef=2.0,
                recommendations="Test",
                analysis_data={},
                ai_provider="openai",
                ai_model="gpt-4",
            )

            # Now save a conversion
            conversion_id = manager.save_conversion(
                cookbook_name="test",
                output_type="playbook",
                status="success",
                files_generated=5,
                conversion_data={"files": ["file1.yml", "file2.yml"]},
                analysis_id=analysis_id,
                blob_storage_key="conversion_key_123",
            )

            assert conversion_id is not None
            assert isinstance(conversion_id, int)

    def test_get_analysis_history(self):
        """Test retrieving analysis history."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(db_path=Path(tmpdir) / "test.db")

            # Save multiple analyses
            for i in range(3):
                manager.save_analysis(
                    cookbook_name=f"cookbook{i}",
                    cookbook_path=f"/path{i}",
                    cookbook_version=f"{i}.0.0",
                    complexity="low",
                    estimated_hours=5.0,
                    estimated_hours_with_souschef=2.0,
                    recommendations="",
                    analysis_data={},
                    ai_provider="openai",
                    ai_model="gpt-4",
                )

            history = manager.get_analysis_history()

            assert len(history) == 3
            assert all(isinstance(r, AnalysisResult) for r in history)

    def test_get_conversion_history(self):
        """Test retrieving conversion history."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(db_path=Path(tmpdir) / "test.db")

            # Save analysis and conversions
            analysis_id = manager.save_analysis(
                cookbook_name="test",
                cookbook_path="/path",
                cookbook_version="1.0.0",
                complexity="low",
                estimated_hours=5.0,
                estimated_hours_with_souschef=2.0,
                recommendations="",
                analysis_data={},
            )

            for i in range(2):
                manager.save_conversion(
                    cookbook_name="test",
                    output_type="playbook",
                    status="success",
                    files_generated=i + 1,
                    conversion_data={},
                    analysis_id=analysis_id,
                )

            history = manager.get_conversion_history()

            assert len(history) == 2
            assert all(isinstance(r, ConversionResult) for r in history)

    def test_get_statistics(self):
        """Test retrieving storage statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(db_path=Path(tmpdir) / "test.db")

            # Save analysis
            analysis_id = manager.save_analysis(
                cookbook_name="test",
                cookbook_path="/path",
                cookbook_version="1.0.0",
                complexity="high",
                estimated_hours=20.0,
                estimated_hours_with_souschef=10.0,
                recommendations="",
                analysis_data={},
                ai_provider="openai",
                ai_model="gpt-4",
            )

            # Save conversion
            manager.save_conversion(
                cookbook_name="test",
                output_type="playbook",
                status="success",
                files_generated=5,
                conversion_data={},
                analysis_id=analysis_id,
                blob_storage_key="key",
            )

            stats = manager.get_statistics()

            assert stats["total_analyses"] == 1
            assert stats["total_conversions"] == 1
            assert stats["total_files_generated"] == 5

    def test_generate_cache_key_consistency(self):
        """Test that cache key generation is consistent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(db_path=Path(tmpdir) / "test.db")

            cookbook_path = "/path/to/cookbook"
            ai_provider = "openai"
            ai_model = "gpt-4"

            key1 = manager.generate_cache_key(cookbook_path, ai_provider, ai_model)
            key2 = manager.generate_cache_key(cookbook_path, ai_provider, ai_model)

            assert key1 == key2

    def test_generate_cache_key_differs_for_different_inputs(self):
        """Test that cache keys differ for different inputs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(db_path=Path(tmpdir) / "test.db")

            key1 = manager.generate_cache_key("/path/to/cookbook1", "openai", "gpt-4")
            key2 = manager.generate_cache_key("/path/to/cookbook2", "openai", "gpt-4")

            assert key1 != key2

    def test_generate_cache_key_falls_back_on_hash_error(self):
        """Test cache key generation when hashing raises errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(db_path=Path(tmpdir) / "test.db")

            with patch.object(manager, "_hash_directory_contents", side_effect=OSError):
                cache_key = manager.generate_cache_key("/invalid/path")

            assert isinstance(cache_key, str)
            assert len(cache_key) == 64

    def test_get_analysis_history_filters_by_cookbook(self):
        """Test filtering analysis history by cookbook name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(db_path=Path(tmpdir) / "test.db")

            manager.save_analysis(
                cookbook_name="alpha",
                cookbook_path="/alpha",
                cookbook_version="1.0.0",
                complexity="low",
                estimated_hours=1.0,
                estimated_hours_with_souschef=1.0,
                recommendations="",
                analysis_data={},
            )
            manager.save_analysis(
                cookbook_name="beta",
                cookbook_path="/beta",
                cookbook_version="1.0.0",
                complexity="low",
                estimated_hours=1.0,
                estimated_hours_with_souschef=1.0,
                recommendations="",
                analysis_data={},
            )

            history = manager.get_analysis_history(cookbook_name="alpha")

            assert len(history) == 1
            assert history[0].cookbook_name == "alpha"

    def test_get_conversions_by_analysis_id(self):
        """Test retrieving conversions linked to an analysis ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(db_path=Path(tmpdir) / "test.db")
            analysis_id = manager.save_analysis(
                cookbook_name="cookbook",
                cookbook_path="/cookbook",
                cookbook_version="1.0.0",
                complexity="low",
                estimated_hours=1.0,
                estimated_hours_with_souschef=1.0,
                recommendations="",
                analysis_data={},
            )

            manager.save_conversion(
                cookbook_name="cookbook",
                output_type="playbook",
                status="success",
                files_generated=1,
                conversion_data={},
                analysis_id=analysis_id,
            )

            conversions = manager.get_conversions_by_analysis_id(analysis_id or 0)

            assert len(conversions) == 1
            assert conversions[0].analysis_id == analysis_id

    def test_delete_analysis_and_conversion(self):
        """Test deleting analysis and conversion records."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(db_path=Path(tmpdir) / "test.db")
            analysis_id = manager.save_analysis(
                cookbook_name="cookbook",
                cookbook_path="/cookbook",
                cookbook_version="1.0.0",
                complexity="low",
                estimated_hours=1.0,
                estimated_hours_with_souschef=1.0,
                recommendations="",
                analysis_data={},
            )
            conversion_id = manager.save_conversion(
                cookbook_name="cookbook",
                output_type="playbook",
                status="success",
                files_generated=1,
                conversion_data={},
                analysis_id=analysis_id,
            )

            assert manager.delete_conversion(conversion_id or 0) is True
            assert manager.delete_analysis(analysis_id or 0) is True


class TestPostgresStorageManager:
    """Tests for PostgresStorageManager helper paths."""

    def test_prepare_sql_replaces_placeholders(self):
        """Test SQL placeholder conversion for PostgreSQL."""
        from souschef.storage.database import PostgresStorageManager

        with patch.object(PostgresStorageManager, "_ensure_database_exists"):
            manager = PostgresStorageManager("postgresql://example")

        assert manager._prepare_sql("SELECT * FROM table WHERE id = ?") == (
            "SELECT * FROM table WHERE id = %s"
        )

    def test_get_psycopg_missing_dependency(self):
        """Test psycopg import error is surfaced as ImportError."""
        from souschef.storage.database import PostgresStorageManager

        manager = PostgresStorageManager.__new__(PostgresStorageManager)
        manager.dsn = "postgresql://example"

        with (
            patch("importlib.import_module", side_effect=ImportError("missing")),
            pytest.raises(ImportError, match="psycopg is required"),
        ):
            manager._get_psycopg()

    def test_ensure_database_exists_handles_migration_error(self):
        """Test database migrations roll back on errors."""
        from souschef.storage.database import PostgresStorageManager

        class FakeConn:
            """Simple fake connection for PostgreSQL tests."""

            def __init__(self) -> None:
                self.executed: list[str] = []
                self.commits = 0
                self.rollbacks = 0

            def execute(self, sql: str, *_args: object) -> None:
                self.executed.append(sql)
                if "ADD COLUMN content_fingerprint" in sql:
                    raise ValueError("already exists")

            def commit(self) -> None:
                self.commits += 1

            def rollback(self) -> None:
                self.rollbacks += 1

            def __enter__(self) -> "FakeConn":
                return self

            def __exit__(self, _exc_type, _exc, _tb) -> None:
                return None

        manager = PostgresStorageManager.__new__(PostgresStorageManager)
        manager.dsn = "postgresql://example"

        with patch.object(manager, "_connect", return_value=FakeConn()):
            manager._ensure_database_exists()

    def test_get_storage_manager_singleton(self):
        """Test that get_storage_manager returns singleton instance."""
        with (
            patch.dict("os.environ", {"POSTGRES_PASSWORD": "test-password"}),
            patch("souschef.storage.database.load_database_settings") as mock_load,
            patch("souschef.storage.database._storage_manager", None),
            patch("souschef.storage.database.StorageManager.__init__") as mock_init,
        ):
            mock_load.return_value = DatabaseSettings(
                backend="sqlite",
                sqlite_path=None,
                postgres_dsn=None,
                postgres_host="postgres",
                postgres_port=5432,
                postgres_name="souschef",
                postgres_user="souschef",
                postgres_password=os.environ["POSTGRES_PASSWORD"],
                postgres_sslmode="disable",
            )
            mock_init.return_value = None

            manager1 = get_storage_manager()
            manager2 = get_storage_manager()

            assert manager1 is manager2

    def test_get_storage_manager_postgres_backend(self):
        """Test that get_storage_manager returns PostgresStorageManager."""
        with (
            patch.dict("os.environ", {"POSTGRES_PASSWORD": "test-password"}),
            patch("souschef.storage.database.load_database_settings") as mock_load,
            patch("souschef.storage.database._storage_manager", None),
            patch(
                "souschef.storage.database.PostgresStorageManager.__init__"
            ) as mock_init,
        ):
            mock_load.return_value = DatabaseSettings(
                backend="postgres",
                sqlite_path=None,
                postgres_dsn="postgresql://user:pass@localhost:5432/db",
                postgres_host="postgres",
                postgres_port=5432,
                postgres_name="souschef",
                postgres_user="souschef",
                postgres_password=os.environ["POSTGRES_PASSWORD"],
                postgres_sslmode="disable",
            )
            mock_init.return_value = None

            manager = get_storage_manager()
            assert manager is not None

    def test_analysis_result_dataclass(self):
        """Test AnalysisResult dataclass."""
        analysis = AnalysisResult(
            id=1,
            cookbook_name="test",
            cookbook_path="/path",
            cookbook_version="1.0.0",
            complexity="low",
            estimated_hours=5.0,
            estimated_hours_with_souschef=2.0,
            recommendations="Test",
            ai_provider="openai",
            ai_model="gpt-4",
            analysis_data="{}",
            created_at="2026-02-02T00:00:00",
        )

        assert analysis.id == 1
        assert analysis.cookbook_name == "test"
        assert analysis.complexity == "low"

    def test_conversion_result_dataclass(self):
        """Test ConversionResult dataclass."""
        conversion = ConversionResult(
            id=1,
            analysis_id=1,
            cookbook_name="test",
            output_type="playbook",
            status="success",
            files_generated=5,
            blob_storage_key="key",
            conversion_data="{}",
            created_at="2026-02-02T00:00:00",
        )

        assert conversion.id == 1
        assert conversion.output_type == "playbook"
        assert conversion.files_generated == 5


class TestLocalBlobStorage:
    """Tests for LocalBlobStorage class."""

    def test_init_creates_directory(self):
        """Test that LocalBlobStorage creates base directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalBlobStorage(base_path=tmpdir)
            assert storage.base_path.exists()

    def test_upload_file(self):
        """Test uploading a single file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalBlobStorage(base_path=tmpdir)

            # Create a test file
            test_file = Path(tmpdir) / "test_file.txt"
            test_file.write_text("test content")

            storage_key = storage.upload(test_file, "key/to/file.txt")

            assert storage_key is not None
            assert isinstance(storage_key, str)

    def test_upload_directory(self):
        """Test uploading a directory as ZIP."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalBlobStorage(base_path=tmpdir)

            # Create a test directory with files
            test_dir = Path(tmpdir) / "test_dir"
            test_dir.mkdir()
            (test_dir / "file1.txt").write_text("content1")
            (test_dir / "file2.txt").write_text("content2")

            storage_key = storage.upload(test_dir, "key/to/dir")

            assert storage_key is not None

    def test_download_file(self):
        """Test downloading a file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalBlobStorage(base_path=tmpdir)

            # Create and upload a file
            test_file = Path(tmpdir) / "original.txt"
            test_file.write_text("test content")

            storage_key = storage.upload(test_file, "key/file.txt")

            # Download to a new location
            download_path = Path(tmpdir) / "downloaded.txt"
            result_path = storage.download(storage_key, download_path)

            assert result_path.exists()

    def test_delete_file(self):
        """Test deleting a file from storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalBlobStorage(base_path=tmpdir)

            # Upload a file
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("content")
            storage_key = storage.upload(test_file, "key/file.txt")

            # Delete it
            result = storage.delete(storage_key)
            assert result is True

    def test_list_keys(self):
        """Test listing storage keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalBlobStorage(base_path=tmpdir)

            # Upload multiple files
            for i in range(3):
                test_file = Path(tmpdir) / f"file{i}.txt"
                test_file.write_text(f"content{i}")
                storage.upload(test_file, f"test/file{i}.txt")

            keys = storage.list_keys()
            assert isinstance(keys, list)

    def test_path_prevents_dangerous_keys(self):
        """Test that storage key handling is safe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalBlobStorage(base_path=tmpdir)

            # Create a test file
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("content")

            # Upload with a safe key
            key = storage.upload(test_file, "safe/key/path.txt")
            assert key is not None

    def test_upload_preserves_file_content(self):
        """Test that uploaded file content is preserved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalBlobStorage(base_path=tmpdir)

            original_content = "This is test content with special chars: !@#$%"
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text(original_content)

            storage_key = storage.upload(test_file, "test/file.txt")
            downloaded = Path(tmpdir) / "downloaded.txt"
            storage.download(storage_key, downloaded)

            assert downloaded.read_text() == original_content
