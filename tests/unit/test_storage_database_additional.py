"""Additional comprehensive tests for storage database module."""

import sqlite3
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

from souschef.storage.database import (
    AnalysisResult,
    PostgresStorageManager,
    StorageManager,
    _analysis_from_row,
    _conversion_from_row,
    calculate_file_fingerprint,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Create a temporary database path."""
    return tmp_path / "test.db"


@pytest.fixture
def storage_manager(temp_db_path: Path) -> Generator[StorageManager, Any, None]:
    """Create a test StorageManager instance."""
    manager = StorageManager(db_path=str(temp_db_path))
    yield manager
    manager.close()


@pytest.fixture
def sample_analysis_data() -> dict[str, Any]:
    """Create sample analysis data."""
    return {
        "complexity_score": 75,
        "recipes_count": 5,
        "resources_count": 20,
        "patterns": ["service", "package", "template"],
    }


@pytest.fixture
def sample_conversion_data() -> dict[str, Any]:
    """Create sample conversion data."""
    return {
        "tasks_created": 15,
        "files": ["main.yml", "vars.yml"],
        "warnings": ["deprecated_resource"],
    }


# ============================================================================
# Tests: StorageManager Error Handling
# ============================================================================


class TestStorageManagerErrorHandling:
    """Test error handling paths in StorageManager."""

    def test_close_handles_database_error(self, temp_db_path: Path) -> None:
        """Test close() handles database errors gracefully."""
        manager = StorageManager(db_path=str(temp_db_path))

        # Mock sqlite3.connect to raise an error on the second call (in close)
        with mock.patch(
            "sqlite3.connect", side_effect=sqlite3.Error("Connection failed")
        ):
            # Should not raise even with connection error
            manager.close()

    def test_close_handles_connection_error(
        self, storage_manager: StorageManager
    ) -> None:
        """Test close() handles connection errors without propagating."""
        original_connect = storage_manager._connect

        def failing_connect(*args: Any, **kwargs: Any) -> Any:
            raise sqlite3.Error("Connection failed")

        storage_manager._connect = failing_connect
        # Should not raise
        storage_manager.close()

        storage_manager._connect = original_connect

    def test_delete_analysis_handles_database_error(
        self, storage_manager: StorageManager
    ) -> None:
        """Test delete_analysis() returns False on database error."""
        # Mock the connection to raise an error
        with mock.patch.object(
            storage_manager, "_connect", side_effect=sqlite3.Error("DB error")
        ):
            result = storage_manager.delete_analysis(999)
            assert result is False

    def test_delete_conversion_handles_database_error(
        self, storage_manager: StorageManager
    ) -> None:
        """Test delete_conversion() returns False on database error."""
        with mock.patch.object(
            storage_manager, "_connect", side_effect=sqlite3.Error("DB error")
        ):
            result = storage_manager.delete_conversion(999)
            assert result is False


# ============================================================================
# Tests: Analysis Result Operations on SQLite
# ============================================================================


class TestAnalysisResultOperations:
    """Test analysis result save, retrieve, and delete operations."""

    def test_save_analysis_returns_id(
        self,
        storage_manager: StorageManager,
        sample_analysis_data: dict[str, Any],
    ) -> None:
        """Test save_analysis returns valid ID."""
        analysis_id = storage_manager.save_analysis(
            cookbook_name="test-cookbook",
            cookbook_path="/path/to/cookbook",
            cookbook_version="1.0.0",
            complexity="high",
            estimated_hours=40.0,
            estimated_hours_with_souschef=10.0,
            recommendations="Refactor templates",
            analysis_data=sample_analysis_data,
            ai_provider="openai",
            ai_model="gpt-4",
        )

        assert analysis_id is not None
        assert isinstance(analysis_id, int)
        assert analysis_id > 0

    def test_save_analysis_with_fingerprint_deduplication(
        self,
        storage_manager: StorageManager,
        sample_analysis_data: dict[str, Any],
    ) -> None:
        """Test save_analysis deduplicates by fingerprint."""
        fingerprint = "abc123def456"

        # Save first analysis with fingerprint
        id1 = storage_manager.save_analysis(
            cookbook_name="cookbook1",
            cookbook_path="/path1",
            cookbook_version="1.0.0",
            complexity="high",
            estimated_hours=40.0,
            estimated_hours_with_souschef=10.0,
            recommendations="Test",
            analysis_data=sample_analysis_data,
            content_fingerprint=fingerprint,
        )

        # Save second analysis with same fingerprint
        id2 = storage_manager.save_analysis(
            cookbook_name="cookbook2",
            cookbook_path="/path2",
            cookbook_version="2.0.0",
            complexity="low",
            estimated_hours=20.0,
            estimated_hours_with_souschef=5.0,
            recommendations="Different",
            analysis_data=sample_analysis_data,
            content_fingerprint=fingerprint,
        )

        # Should return same ID (deduplication)
        assert id1 == id2

    def test_save_analysis_with_blob_key(
        self,
        storage_manager: StorageManager,
        sample_analysis_data: dict[str, Any],
    ) -> None:
        """Test save_analysis with blob storage key."""
        blob_key = "s3://bucket/cookbook-archive.tar.gz"

        analysis_id = storage_manager.save_analysis(
            cookbook_name="test-cookbook",
            cookbook_path="/path/to/cookbook",
            cookbook_version="1.0.0",
            complexity="medium",
            estimated_hours=30.0,
            estimated_hours_with_souschef=8.0,
            recommendations="Test",
            analysis_data=sample_analysis_data,
            cookbook_blob_key=blob_key,
        )

        assert analysis_id is not None

        # Retrieve and verify blob key is stored
        history = storage_manager.get_analysis_history(limit=1)
        assert len(history) > 0
        assert history[0].cookbook_blob_key == blob_key

    def test_get_analysis_by_fingerprint_returns_existing(
        self,
        storage_manager: StorageManager,
        sample_analysis_data: dict[str, Any],
    ) -> None:
        """Test get_analysis_by_fingerprint returns existing analysis."""
        fingerprint = "test_fingerprint_123"

        storage_manager.save_analysis(
            cookbook_name="test-cookbook",
            cookbook_path="/path",
            cookbook_version="1.0.0",
            complexity="high",
            estimated_hours=40.0,
            estimated_hours_with_souschef=10.0,
            recommendations="Test",
            analysis_data=sample_analysis_data,
            content_fingerprint=fingerprint,
        )

        result = storage_manager.get_analysis_by_fingerprint(fingerprint)

        assert result is not None
        assert result.cookbook_name == "test-cookbook"
        assert result.content_fingerprint == fingerprint

    def test_get_analysis_by_fingerprint_not_found(
        self, storage_manager: StorageManager
    ) -> None:
        """Test get_analysis_by_fingerprint returns None when not found."""
        result = storage_manager.get_analysis_by_fingerprint("nonexistent")
        assert result is None

    def test_delete_analysis_removes_conversions(
        self,
        storage_manager: StorageManager,
        sample_analysis_data: dict[str, Any],
        sample_conversion_data: dict[str, Any],
    ) -> None:
        """Test delete_analysis also deletes associated conversions."""
        analysis_id = storage_manager.save_analysis(
            cookbook_name="test-cookbook",
            cookbook_path="/path",
            cookbook_version="1.0.0",
            complexity="high",
            estimated_hours=40.0,
            estimated_hours_with_souschef=10.0,
            recommendations="Test",
            analysis_data=sample_analysis_data,
        )

        assert analysis_id is not None

        conversion_id = storage_manager.save_conversion(
            cookbook_name="test-cookbook",
            output_type="playbook",
            status="success",
            files_generated=3,
            conversion_data=sample_conversion_data,
            analysis_id=analysis_id,
        )

        assert conversion_id is not None

        # Delete analysis
        result = storage_manager.delete_analysis(analysis_id)
        assert result is True

        # Verify conversion is also deleted
        conversions = storage_manager.get_conversions_by_analysis_id(analysis_id)
        assert len(conversions) == 0

    def test_delete_analysis_with_nonexistent_id(
        self, storage_manager: StorageManager
    ) -> None:
        """Test delete_analysis returns False for nonexistent ID."""
        result = storage_manager.delete_analysis(99999)
        assert result is False

    def test_delete_analysis_returns_true_on_success(
        self,
        storage_manager: StorageManager,
        sample_analysis_data: dict[str, Any],
    ) -> None:
        """Test delete_analysis returns True when deletion succeeds."""
        analysis_id = storage_manager.save_analysis(
            cookbook_name="test-cookbook",
            cookbook_path="/path",
            cookbook_version="1.0.0",
            complexity="high",
            estimated_hours=40.0,
            estimated_hours_with_souschef=10.0,
            recommendations="Test",
            analysis_data=sample_analysis_data,
        )

        assert analysis_id is not None
        result = storage_manager.delete_analysis(analysis_id)
        assert result is True


# ============================================================================
# Tests: Conversion Result Operations on SQLite
# ============================================================================


class TestConversionResultOperations:
    """Test conversion result save, retrieve, and delete operations."""

    def test_save_conversion_returns_id(
        self,
        storage_manager: StorageManager,
        sample_conversion_data: dict[str, Any],
    ) -> None:
        """Test save_conversion returns valid ID."""
        conversion_id = storage_manager.save_conversion(
            cookbook_name="test-cookbook",
            output_type="playbook",
            status="success",
            files_generated=5,
            conversion_data=sample_conversion_data,
        )

        assert conversion_id is not None
        assert isinstance(conversion_id, int)
        assert conversion_id > 0

    def test_save_conversion_with_analysis_id(
        self,
        storage_manager: StorageManager,
        sample_analysis_data: dict[str, Any],
        sample_conversion_data: dict[str, Any],
    ) -> None:
        """Test save_conversion with analysis_id association."""
        analysis_id = storage_manager.save_analysis(
            cookbook_name="test-cookbook",
            cookbook_path="/path",
            cookbook_version="1.0.0",
            complexity="high",
            estimated_hours=40.0,
            estimated_hours_with_souschef=10.0,
            recommendations="Test",
            analysis_data=sample_analysis_data,
        )

        conversion_id = storage_manager.save_conversion(
            cookbook_name="test-cookbook",
            output_type="playbook",
            status="success",
            files_generated=5,
            conversion_data=sample_conversion_data,
            analysis_id=analysis_id,
        )

        assert conversion_id is not None

        assert analysis_id is not None  # Narrow type for type checker
        conversions = storage_manager.get_conversions_by_analysis_id(analysis_id)
        assert len(conversions) > 0
        assert conversions[0].analysis_id is not None
        assert conversions[0].analysis_id == analysis_id

    def test_save_conversion_with_blob_storage_key(
        self,
        storage_manager: StorageManager,
        sample_conversion_data: dict[str, Any],
    ) -> None:
        """Test save_conversion with blob storage key."""
        blob_key = "s3://bucket/conversion-output.zip"

        conversion_id = storage_manager.save_conversion(
            cookbook_name="test-cookbook",
            output_type="role",
            status="success",
            files_generated=3,
            conversion_data=sample_conversion_data,
            blob_storage_key=blob_key,
        )

        assert conversion_id is not None

        history = storage_manager.get_conversion_history(limit=1)
        assert len(history) > 0
        assert history[0].blob_storage_key == blob_key

    def test_delete_conversion_returns_true_on_success(
        self,
        storage_manager: StorageManager,
        sample_conversion_data: dict[str, Any],
    ) -> None:
        """Test delete_conversion returns True on success."""
        conversion_id = storage_manager.save_conversion(
            cookbook_name="test-cookbook",
            output_type="playbook",
            status="success",
            files_generated=5,
            conversion_data=sample_conversion_data,
        )

        assert conversion_id is not None
        result = storage_manager.delete_conversion(conversion_id)
        assert result is True

    def test_delete_conversion_with_nonexistent_id(
        self, storage_manager: StorageManager
    ) -> None:
        """Test delete_conversion returns False for nonexistent ID."""
        result = storage_manager.delete_conversion(99999)
        assert result is False


# ============================================================================
# Tests: PostgreSQL Storage Manager Initialization
# ============================================================================


class TestPostgresStorageManagerInit:
    """Test PostgreSQL storage manager initialization."""

    @mock.patch("souschef.storage.database.importlib.import_module")
    def test_postgres_manager_init(self, mock_import: mock.MagicMock) -> None:
        """Test PostgreSQL manager initialisation."""
        mock_psycopg = mock.MagicMock()
        mock_import.return_value = mock_psycopg
        mock_conn = mock.MagicMock()
        mock_psycopg.connect.return_value.__enter__.return_value = mock_conn
        mock_psycopg.connect.return_value.__exit__.return_value = None
        mock_conn.execute.return_value = None
        mock_conn.commit.return_value = None

        dsn = "postgresql://user:pass@localhost/testdb"
        manager = PostgresStorageManager(dsn)

        assert manager.dsn == dsn
        mock_import.assert_called_with("psycopg")

    @mock.patch("souschef.storage.database.importlib.import_module")
    def test_postgres_manager_missing_psycopg(
        self, mock_import: mock.MagicMock
    ) -> None:
        """Test PostgreSQL manager raises when psycopg is missing."""
        mock_import.side_effect = ImportError("No module named psycopg")

        with pytest.raises(ImportError) as exc_info:
            PostgresStorageManager("postgresql://user:pass@localhost/testdb")

        assert "psycopg is required" in str(exc_info.value)

    @mock.patch("souschef.storage.database.importlib.import_module")
    def test_postgres_ensure_database_exists(self, mock_import: mock.MagicMock) -> None:
        """Test _ensure_database_exists with PostgreSQL."""
        mock_psycopg = mock.MagicMock()
        mock_import.return_value = mock_psycopg
        mock_conn = mock.MagicMock()
        mock_psycopg.connect.return_value.__enter__.return_value = mock_conn
        mock_psycopg.connect.return_value.__exit__.return_value = None
        mock_conn.execute.return_value = None
        mock_conn.commit.return_value = None
        mock_conn.rollback.return_value = None

        PostgresStorageManager("postgresql://user:pass@localhost/testdb")

        # Verify tables and indexes were created
        assert mock_conn.execute.called


# ============================================================================
# Tests: PostgreSQL Analysis Operations
# ============================================================================


class TestPostgresAnalysisOperations:
    """Test PostgreSQL analysis operations."""

    @pytest.fixture
    def postgres_manager(self) -> Any:
        """Create a mocked PostgreSQL manager."""
        with mock.patch("souschef.storage.database.importlib.import_module"):
            manager = mock.MagicMock(spec=PostgresStorageManager)
            manager.dsn = "postgresql://user:pass@localhost/testdb"
            manager._prepare_sql = PostgresStorageManager._prepare_sql.__get__(manager)
            return manager

    def test_prepare_sql_converts_placeholders(self, postgres_manager: Any) -> None:
        """Test _prepare_sql converts SQLite placeholders to PostgreSQL."""
        sql = "INSERT INTO table (col1, col2) VALUES (?, ?)"
        result = postgres_manager._prepare_sql(sql)
        assert result == "INSERT INTO table (col1, col2) VALUES (%s, %s)"

    @mock.patch("souschef.storage.database.importlib.import_module")
    def test_postgres_save_analysis_deduplication(
        self, mock_import: mock.MagicMock, sample_analysis_data: dict[str, Any]
    ) -> None:
        """Test PostgreSQL save_analysis with fingerprint deduplication."""
        mock_psycopg = mock.MagicMock()
        mock_import.return_value = mock_psycopg
        mock_conn = mock.MagicMock()
        mock_cursor = mock.MagicMock()
        mock_psycopg.connect.return_value.__enter__.return_value = mock_conn
        mock_psycopg.connect.return_value.__exit__.return_value = None
        mock_conn.execute.return_value = mock_cursor
        mock_conn.commit.return_value = None

        # Mock get_analysis_by_fingerprint to return existing
        existing = AnalysisResult(
            id=123,
            cookbook_name="existing",
            cookbook_path="/path",
            cookbook_version="1.0",
            complexity="high",
            estimated_hours=40.0,
            estimated_hours_with_souschef=10.0,
            recommendations="Test",
            ai_provider="openai",
            ai_model="gpt-4",
            analysis_data="{}",
            created_at="2026-01-01",
            content_fingerprint="test_fp",
        )

        manager = PostgresStorageManager("postgresql://user:pass@localhost/testdb")

        with mock.patch.object(
            manager, "get_analysis_by_fingerprint", return_value=existing
        ):
            result_id = manager.save_analysis(
                cookbook_name="new",
                cookbook_path="/path",
                cookbook_version="1.0",
                complexity="high",
                estimated_hours=40.0,
                estimated_hours_with_souschef=10.0,
                recommendations="Test",
                analysis_data=sample_analysis_data,
                content_fingerprint="test_fp",
            )

            # Should return existing ID
            assert result_id == 123

    @mock.patch("souschef.storage.database.importlib.import_module")
    def test_postgres_save_analysis_new_record(
        self, mock_import: mock.MagicMock, sample_analysis_data: dict[str, Any]
    ) -> None:
        """Test PostgreSQL save_analysis creates new record."""
        mock_psycopg = mock.MagicMock()
        mock_import.return_value = mock_psycopg
        mock_conn = mock.MagicMock()
        mock_cursor = mock.MagicMock()
        mock_psycopg.connect.return_value.__enter__.return_value = mock_conn
        mock_psycopg.connect.return_value.__exit__.return_value = None
        mock_conn.execute.return_value = mock_cursor
        mock_conn.commit.return_value = None
        mock_cursor.fetchone.return_value = {"id": 456}

        manager = PostgresStorageManager("postgresql://user:pass@localhost/testdb")

        with mock.patch.object(
            manager, "get_analysis_by_fingerprint", return_value=None
        ):
            result_id = manager.save_analysis(
                cookbook_name="new",
                cookbook_path="/path",
                cookbook_version="1.0",
                complexity="high",
                estimated_hours=40.0,
                estimated_hours_with_souschef=10.0,
                recommendations="Test",
                analysis_data=sample_analysis_data,
            )

            assert result_id == 456
            mock_conn.commit.assert_called()

    @mock.patch("souschef.storage.database.importlib.import_module")
    def test_postgres_get_analysis_by_fingerprint(
        self, mock_import: mock.MagicMock
    ) -> None:
        """Test PostgreSQL get_analysis_by_fingerprint."""
        mock_psycopg = mock.MagicMock()
        mock_import.return_value = mock_psycopg
        mock_conn = mock.MagicMock()
        mock_cursor = mock.MagicMock()
        mock_psycopg.connect.return_value.__enter__.return_value = mock_conn
        mock_psycopg.connect.return_value.__exit__.return_value = None
        mock_conn.execute.return_value = mock_cursor

        row_data = {
            "id": 123,
            "cookbook_name": "test",
            "cookbook_path": "/path",
            "cookbook_version": "1.0",
            "complexity": "high",
            "estimated_hours": 40.0,
            "estimated_hours_with_souschef": 10.0,
            "recommendations": "Test",
            "ai_provider": "openai",
            "ai_model": "gpt-4",
            "analysis_data": "{}",
            "created_at": "2026-01-01",
            "content_fingerprint": "abc123",
        }
        mock_cursor.fetchone.return_value = row_data

        manager = PostgresStorageManager("postgresql://user:pass@localhost/testdb")
        result = manager.get_analysis_by_fingerprint("abc123")

        assert result is not None
        assert result.id == 123
        assert result.content_fingerprint == "abc123"

    @mock.patch("souschef.storage.database.importlib.import_module")
    def test_postgres_get_analysis_by_fingerprint_not_found(
        self, mock_import: mock.MagicMock
    ) -> None:
        """Test PostgreSQL get_analysis_by_fingerprint returns None."""
        mock_psycopg = mock.MagicMock()
        mock_import.return_value = mock_psycopg
        mock_conn = mock.MagicMock()
        mock_cursor = mock.MagicMock()
        mock_psycopg.connect.return_value.__enter__.return_value = mock_conn
        mock_psycopg.connect.return_value.__exit__.return_value = None
        mock_conn.execute.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        manager = PostgresStorageManager("postgresql://user:pass@localhost/testdb")
        result = manager.get_analysis_by_fingerprint("nonexistent")

        assert result is None

    @mock.patch("souschef.storage.database.importlib.import_module")
    def test_postgres_get_cached_analysis(self, mock_import: mock.MagicMock) -> None:
        """Test PostgreSQL get_cached_analysis."""
        mock_psycopg = mock.MagicMock()
        mock_import.return_value = mock_psycopg
        mock_conn = mock.MagicMock()
        mock_cursor = mock.MagicMock()
        mock_psycopg.connect.return_value.__enter__.return_value = mock_conn
        mock_psycopg.connect.return_value.__exit__.return_value = None
        mock_conn.execute.return_value = mock_cursor

        row_data = {
            "id": 456,
            "cookbook_name": "cached",
            "cookbook_path": "/path",
            "cookbook_version": "1.0",
            "complexity": "medium",
            "estimated_hours": 30.0,
            "estimated_hours_with_souschef": 8.0,
            "recommendations": "Test",
            "ai_provider": "openai",
            "ai_model": "gpt-4",
            "analysis_data": "{}",
            "created_at": "2026-01-01",
            "cache_key": "cache_key_123",
        }
        mock_cursor.fetchone.return_value = row_data

        manager = PostgresStorageManager("postgresql://user:pass@localhost/testdb")
        result = manager.get_cached_analysis(
            "/path",
            ai_provider="openai",
            ai_model="gpt-4",
        )

        assert result is not None
        assert result.id == 456
        assert result.cookbook_name == "cached"

    @mock.patch("souschef.storage.database.importlib.import_module")
    def test_postgres_get_cached_analysis_not_found(
        self, mock_import: mock.MagicMock
    ) -> None:
        """Test PostgreSQL get_cached_analysis returns None."""
        mock_psycopg = mock.MagicMock()
        mock_import.return_value = mock_psycopg
        mock_conn = mock.MagicMock()
        mock_cursor = mock.MagicMock()
        mock_psycopg.connect.return_value.__enter__.return_value = mock_conn
        mock_psycopg.connect.return_value.__exit__.return_value = None
        mock_conn.execute.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        manager = PostgresStorageManager("postgresql://user:pass@localhost/testdb")
        result = manager.get_cached_analysis("/path")

        assert result is None


# ============================================================================
# Tests: PostgreSQL Conversion Operations
# ============================================================================


class TestPostgresConversionOperations:
    """Test PostgreSQL conversion operations."""

    @mock.patch("souschef.storage.database.importlib.import_module")
    def test_postgres_save_conversion(
        self, mock_import: mock.MagicMock, sample_conversion_data: dict[str, Any]
    ) -> None:
        """Test PostgreSQL save_conversion."""
        mock_psycopg = mock.MagicMock()
        mock_import.return_value = mock_psycopg
        mock_conn = mock.MagicMock()
        mock_cursor = mock.MagicMock()
        mock_psycopg.connect.return_value.__enter__.return_value = mock_conn
        mock_psycopg.connect.return_value.__exit__.return_value = None
        mock_conn.execute.return_value = mock_cursor
        mock_conn.commit.return_value = None
        mock_cursor.fetchone.return_value = {"id": 789}

        manager = PostgresStorageManager("postgresql://user:pass@localhost/testdb")
        result_id = manager.save_conversion(
            cookbook_name="test",
            output_type="playbook",
            status="success",
            files_generated=5,
            conversion_data=sample_conversion_data,
            analysis_id=123,
        )

        assert result_id == 789
        mock_conn.commit.assert_called()

    @mock.patch("souschef.storage.database.importlib.import_module")
    def test_postgres_save_conversion_no_analysis_id(
        self, mock_import: mock.MagicMock, sample_conversion_data: dict[str, Any]
    ) -> None:
        """Test PostgreSQL save_conversion without analysis_id."""
        mock_psycopg = mock.MagicMock()
        mock_import.return_value = mock_psycopg
        mock_conn = mock.MagicMock()
        mock_cursor = mock.MagicMock()
        mock_psycopg.connect.return_value.__enter__.return_value = mock_conn
        mock_psycopg.connect.return_value.__exit__.return_value = None
        mock_conn.execute.return_value = mock_cursor
        mock_conn.commit.return_value = None
        mock_cursor.fetchone.return_value = {"id": 999}

        manager = PostgresStorageManager("postgresql://user:pass@localhost/testdb")
        result_id = manager.save_conversion(
            cookbook_name="test",
            output_type="role",
            status="success",
            files_generated=3,
            conversion_data=sample_conversion_data,
        )

        assert result_id == 999


# ============================================================================
# Tests: PostgreSQL History and Retrieval
# ============================================================================


class TestPostgresHistoryRetrieval:
    """Test PostgreSQL history and retrieval operations."""

    @mock.patch("souschef.storage.database.importlib.import_module")
    def test_postgres_get_analysis_history(self, mock_import: mock.MagicMock) -> None:
        """Test PostgreSQL get_analysis_history."""
        mock_psycopg = mock.MagicMock()
        mock_import.return_value = mock_psycopg
        mock_conn = mock.MagicMock()
        mock_cursor = mock.MagicMock()
        mock_psycopg.connect.return_value.__enter__.return_value = mock_conn
        mock_psycopg.connect.return_value.__exit__.return_value = None
        mock_conn.execute.return_value = mock_cursor

        row_data = {
            "id": 111,
            "cookbook_name": "test",
            "cookbook_path": "/path",
            "cookbook_version": "1.0",
            "complexity": "high",
            "estimated_hours": 40.0,
            "estimated_hours_with_souschef": 10.0,
            "recommendations": "Test",
            "ai_provider": "openai",
            "ai_model": "gpt-4",
            "analysis_data": "{}",
            "created_at": "2026-01-01",
        }
        mock_cursor.fetchall.return_value = [row_data]

        manager = PostgresStorageManager("postgresql://user:pass@localhost/testdb")
        results = manager.get_analysis_history(cookbook_name="test", limit=25)

        assert len(results) == 1
        assert results[0].id == 111

    @mock.patch("souschef.storage.database.importlib.import_module")
    def test_postgres_get_analysis_history_all(
        self, mock_import: mock.MagicMock
    ) -> None:
        """Test PostgreSQL get_analysis_history without cookbook filter."""
        mock_psycopg = mock.MagicMock()
        mock_import.return_value = mock_psycopg
        mock_conn = mock.MagicMock()
        mock_cursor = mock.MagicMock()
        mock_psycopg.connect.return_value.__enter__.return_value = mock_conn
        mock_psycopg.connect.return_value.__exit__.return_value = None
        mock_conn.execute.return_value = mock_cursor

        row_data_1 = {
            "id": 111,
            "cookbook_name": "test1",
            "cookbook_path": "/path1",
            "cookbook_version": "1.0",
            "complexity": "high",
            "estimated_hours": 40.0,
            "estimated_hours_with_souschef": 10.0,
            "recommendations": "Test",
            "ai_provider": "openai",
            "ai_model": "gpt-4",
            "analysis_data": "{}",
            "created_at": "2026-01-01",
        }
        row_data_2 = {
            "id": 222,
            "cookbook_name": "test2",
            "cookbook_path": "/path2",
            "cookbook_version": "2.0",
            "complexity": "low",
            "estimated_hours": 20.0,
            "estimated_hours_with_souschef": 5.0,
            "recommendations": "Test",
            "ai_provider": "anthropic",
            "ai_model": "claude",
            "analysis_data": "{}",
            "created_at": "2026-01-02",
        }
        mock_cursor.fetchall.return_value = [row_data_1, row_data_2]

        manager = PostgresStorageManager("postgresql://user:pass@localhost/testdb")
        results = manager.get_analysis_history()

        assert len(results) == 2
        assert results[0].id == 111
        assert results[1].id == 222

    @mock.patch("souschef.storage.database.importlib.import_module")
    def test_postgres_get_conversion_history(self, mock_import: mock.MagicMock) -> None:
        """Test PostgreSQL get_conversion_history."""
        mock_psycopg = mock.MagicMock()
        mock_import.return_value = mock_psycopg
        mock_conn = mock.MagicMock()
        mock_cursor = mock.MagicMock()
        mock_psycopg.connect.return_value.__enter__.return_value = mock_conn
        mock_psycopg.connect.return_value.__exit__.return_value = None
        mock_conn.execute.return_value = mock_cursor

        row_data = {
            "id": 333,
            "analysis_id": 111,
            "cookbook_name": "test",
            "output_type": "playbook",
            "status": "success",
            "files_generated": 5,
            "blob_storage_key": "s3://bucket/file",
            "conversion_data": "{}",
            "created_at": "2026-01-01",
        }
        mock_cursor.fetchall.return_value = [row_data]

        manager = PostgresStorageManager("postgresql://user:pass@localhost/testdb")
        results = manager.get_conversion_history(cookbook_name="test", limit=25)

        assert len(results) == 1
        assert results[0].id == 333
        assert results[0].status == "success"

    @mock.patch("souschef.storage.database.importlib.import_module")
    def test_postgres_get_conversions_by_analysis_id(
        self, mock_import: mock.MagicMock
    ) -> None:
        """Test PostgreSQL get_conversions_by_analysis_id."""
        mock_psycopg = mock.MagicMock()
        mock_import.return_value = mock_psycopg
        mock_conn = mock.MagicMock()
        mock_cursor = mock.MagicMock()
        mock_psycopg.connect.return_value.__enter__.return_value = mock_conn
        mock_psycopg.connect.return_value.__exit__.return_value = None
        mock_conn.execute.return_value = mock_cursor

        row_data_1 = {
            "id": 333,
            "analysis_id": 111,
            "cookbook_name": "test",
            "output_type": "playbook",
            "status": "success",
            "files_generated": 5,
            "blob_storage_key": None,
            "conversion_data": "{}",
            "created_at": "2026-01-01",
        }
        row_data_2 = {
            "id": 444,
            "analysis_id": 111,
            "cookbook_name": "test",
            "output_type": "role",
            "status": "success",
            "files_generated": 3,
            "blob_storage_key": None,
            "conversion_data": "{}",
            "created_at": "2026-01-02",
        }
        mock_cursor.fetchall.return_value = [row_data_1, row_data_2]

        manager = PostgresStorageManager("postgresql://user:pass@localhost/testdb")
        results = manager.get_conversions_by_analysis_id(111)

        assert len(results) == 2
        assert results[0].id == 333
        assert results[1].id == 444
        assert all(r.analysis_id == 111 for r in results)


# ============================================================================
# Tests: PostgreSQL Delete Operations
# ============================================================================


class TestPostgresDeleteOperations:
    """Test PostgreSQL delete operations."""

    @mock.patch("souschef.storage.database.importlib.import_module")
    def test_postgres_delete_analysis_success(
        self, mock_import: mock.MagicMock
    ) -> None:
        """Test PostgreSQL delete_analysis returns True on success."""
        mock_psycopg = mock.MagicMock()
        mock_import.return_value = mock_psycopg
        mock_conn = mock.MagicMock()
        mock_cursor = mock.MagicMock()
        mock_psycopg.connect.return_value.__enter__.return_value = mock_conn
        mock_psycopg.connect.return_value.__exit__.return_value = None
        mock_conn.execute.return_value = mock_cursor
        mock_conn.commit.return_value = None
        mock_cursor.rowcount = 1

        manager = PostgresStorageManager("postgresql://user:pass@localhost/testdb")
        result = manager.delete_analysis(111)

        assert result is True
        mock_conn.commit.assert_called()

    @mock.patch("souschef.storage.database.importlib.import_module")
    def test_postgres_delete_analysis_not_found(
        self, mock_import: mock.MagicMock
    ) -> None:
        """Test PostgreSQL delete_analysis returns False when not found."""
        mock_psycopg = mock.MagicMock()
        mock_import.return_value = mock_psycopg
        mock_conn = mock.MagicMock()
        mock_cursor = mock.MagicMock()
        mock_psycopg.connect.return_value.__enter__.return_value = mock_conn
        mock_psycopg.connect.return_value.__exit__.return_value = None
        mock_conn.execute.return_value = mock_cursor
        mock_conn.commit.return_value = None
        mock_cursor.rowcount = 0

        manager = PostgresStorageManager("postgresql://user:pass@localhost/testdb")
        result = manager.delete_analysis(99999)

        assert result is False

    @mock.patch("souschef.storage.database.importlib.import_module")
    def test_postgres_delete_analysis_handles_exception(
        self, mock_import: mock.MagicMock
    ) -> None:
        """Test PostgreSQL delete_analysis handles exceptions gracefully."""
        mock_psycopg = mock.MagicMock()
        mock_import.return_value = mock_psycopg
        mock_conn = mock.MagicMock()
        mock_psycopg.connect.return_value.__enter__.return_value = mock_conn
        mock_psycopg.connect.return_value.__exit__.return_value = None
        mock_conn.execute.return_value = None
        mock_conn.commit.return_value = None

        with mock.patch.object(
            PostgresStorageManager, "_ensure_database_exists", return_value=None
        ):
            manager = PostgresStorageManager("postgresql://user:pass@localhost/testdb")

            # Mock execute to raise exception when called with delete
            mock_psycopg.connect.return_value.__enter__.return_value.execute.side_effect = Exception(
                "Connection error"
            )

            result = manager.delete_analysis(111)
            assert result is False

    @mock.patch("souschef.storage.database.importlib.import_module")
    def test_postgres_delete_conversion_success(
        self, mock_import: mock.MagicMock
    ) -> None:
        """Test PostgreSQL delete_conversion returns True on success."""
        mock_psycopg = mock.MagicMock()
        mock_import.return_value = mock_psycopg
        mock_conn = mock.MagicMock()
        mock_cursor = mock.MagicMock()
        mock_psycopg.connect.return_value.__enter__.return_value = mock_conn
        mock_psycopg.connect.return_value.__exit__.return_value = None
        mock_conn.execute.return_value = mock_cursor
        mock_conn.commit.return_value = None
        mock_cursor.rowcount = 1

        manager = PostgresStorageManager("postgresql://user:pass@localhost/testdb")
        result = manager.delete_conversion(333)

        assert result is True

    @mock.patch("souschef.storage.database.importlib.import_module")
    def test_postgres_delete_conversion_handles_exception(
        self, mock_import: mock.MagicMock
    ) -> None:
        """Test PostgreSQL delete_conversion handles exceptions gracefully."""
        mock_psycopg = mock.MagicMock()
        mock_import.return_value = mock_psycopg
        mock_conn = mock.MagicMock()
        mock_psycopg.connect.return_value.__enter__.return_value = mock_conn
        mock_psycopg.connect.return_value.__exit__.return_value = None
        mock_conn.execute.return_value = None
        mock_conn.commit.return_value = None

        with mock.patch.object(
            PostgresStorageManager, "_ensure_database_exists", return_value=None
        ):
            manager = PostgresStorageManager("postgresql://user:pass@localhost/testdb")

            # Mock execute to raise exception when called with delete
            mock_psycopg.connect.return_value.__enter__.return_value.execute.side_effect = Exception(
                "Connection error"
            )

            result = manager.delete_conversion(333)
            assert result is False


# ============================================================================
# Tests: PostgreSQL Statistics
# ============================================================================


class TestPostgresStatistics:
    """Test PostgreSQL statistics operations."""

    @mock.patch("souschef.storage.database.importlib.import_module")
    def test_postgres_get_statistics(self, mock_import: mock.MagicMock) -> None:
        """Test PostgreSQL get_statistics."""
        mock_psycopg = mock.MagicMock()
        mock_import.return_value = mock_psycopg
        mock_conn = mock.MagicMock()
        mock_cursor = mock.MagicMock()
        mock_psycopg.connect.return_value.__enter__.return_value = mock_conn
        mock_psycopg.connect.return_value.__exit__.return_value = None
        mock_conn.execute.return_value = mock_cursor

        # Mock first query (analysis stats)
        analysis_row = {
            "total": 10,
            "unique_cookbooks": 5,
            "avg_manual_hours": 35.0,
            "avg_ai_hours": 8.5,
        }
        # Mock second query (conversion stats)
        conversion_row = {
            "total": 15,
            "successful": 12,
            "total_files": 45,
        }
        mock_cursor.fetchone.side_effect = [analysis_row, conversion_row]

        manager = PostgresStorageManager("postgresql://user:pass@localhost/testdb")
        stats = manager.get_statistics()

        assert stats["total_analyses"] == 10
        assert stats["unique_cookbooks_analysed"] == 5
        assert stats["avg_manual_hours"] == pytest.approx(35.0)
        assert stats["avg_ai_hours"] == pytest.approx(8.5)
        assert stats["total_conversions"] == 15
        assert stats["successful_conversions"] == 12
        assert stats["total_files_generated"] == 45


# ============================================================================
# Tests: Helper Functions
# ============================================================================


class TestHelperFunctions:
    """Test helper functions in database module."""

    def test_analysis_from_row_with_dict(self) -> None:
        """Test _analysis_from_row with dict-like row."""
        row_data = {
            "id": 1,
            "cookbook_name": "test",
            "cookbook_path": "/path",
            "cookbook_version": "1.0",
            "complexity": "high",
            "estimated_hours": 40.0,
            "estimated_hours_with_souschef": 10.0,
            "recommendations": "Test",
            "ai_provider": "openai",
            "ai_model": "gpt-4",
            "analysis_data": "{}",
            "created_at": "2026-01-01",
            "cache_key": "key123",
            "cookbook_blob_key": "blob_key",
            "content_fingerprint": "fp123",
        }

        result = _analysis_from_row(row_data)

        assert result.id == 1
        assert result.cookbook_name == "test"
        assert result.cookbook_blob_key == "blob_key"
        assert result.content_fingerprint == "fp123"

    def test_analysis_from_row_missing_optional_fields(self) -> None:
        """Test _analysis_from_row handles missing optional fields."""
        row_data = {
            "id": 1,
            "cookbook_name": "test",
            "cookbook_path": "/path",
            "cookbook_version": "1.0",
            "complexity": "high",
            "estimated_hours": 40.0,
            "estimated_hours_with_souschef": 10.0,
            "recommendations": "Test",
            "ai_provider": "openai",
            "ai_model": "gpt-4",
            "analysis_data": "{}",
            "created_at": "2026-01-01",
            "cache_key": "key123",
        }

        result = _analysis_from_row(row_data)

        assert result.id == 1
        assert result.cookbook_blob_key is None
        assert result.content_fingerprint is None

    def test_conversion_from_row(self) -> None:
        """Test _conversion_from_row."""
        row_data = {
            "id": 10,
            "analysis_id": 1,
            "cookbook_name": "test",
            "output_type": "playbook",
            "status": "success",
            "files_generated": 5,
            "blob_storage_key": "s3://bucket/file",
            "conversion_data": "{}",
            "created_at": "2026-01-01",
        }

        result = _conversion_from_row(row_data)

        assert result.id == 10
        assert result.analysis_id == 1
        assert result.cookbook_name == "test"
        assert result.status == "success"
        assert result.blob_storage_key == "s3://bucket/file"

    def test_calculate_file_fingerprint(self, tmp_path: Path) -> None:
        """Test calculate_file_fingerprint."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        fingerprint = calculate_file_fingerprint(test_file)

        assert isinstance(fingerprint, str)
        assert len(fingerprint) == 64  # SHA256 hex digest length

        # Verify same content produces same fingerprint
        fingerprint2 = calculate_file_fingerprint(test_file)
        assert fingerprint == fingerprint2

    def test_calculate_file_fingerprint_large_file(self, tmp_path: Path) -> None:
        """Test calculate_file_fingerprint with large file."""
        test_file = tmp_path / "large.bin"
        # Create a file larger than chunk size (65536 bytes)
        with test_file.open("wb") as f:
            f.write(b"x" * 100000)

        fingerprint = calculate_file_fingerprint(test_file)

        assert isinstance(fingerprint, str)
        assert len(fingerprint) == 64


# ============================================================================
# Tests: Parametrised Tests
# ============================================================================


class TestParametrisedOperations:
    """Parametrised tests for comprehensive coverage."""

    @pytest.mark.parametrize(
        "complexity,est_hours,ai_hours",
        [
            ("low", 10.0, 2.0),
            ("medium", 25.0, 6.0),
            ("high", 50.0, 12.0),
            ("critical", 100.0, 25.0),
        ],
    )
    def test_save_analysis_various_complexities(
        self,
        storage_manager: StorageManager,
        complexity: str,
        est_hours: float,
        ai_hours: float,
        sample_analysis_data: dict[str, Any],
    ) -> None:
        """Test save_analysis with various complexity levels."""
        analysis_id = storage_manager.save_analysis(
            cookbook_name="test-cookbook",
            cookbook_path="/path",
            cookbook_version="1.0.0",
            complexity=complexity,
            estimated_hours=est_hours,
            estimated_hours_with_souschef=ai_hours,
            recommendations="Test",
            analysis_data=sample_analysis_data,
        )

        assert analysis_id is not None

        history = storage_manager.get_analysis_history(limit=1)
        assert history[0].complexity == complexity
        assert history[0].estimated_hours == est_hours

    @pytest.mark.parametrize(
        "output_type,status",
        [
            ("playbook", "success"),
            ("role", "success"),
            ("collection", "partial"),
            ("playbook", "failed"),
        ],
    )
    def test_save_conversion_various_types_and_status(
        self,
        storage_manager: StorageManager,
        output_type: str,
        status: str,
        sample_conversion_data: dict[str, Any],
    ) -> None:
        """Test save_conversion with various types and statuses."""
        conversion_id = storage_manager.save_conversion(
            cookbook_name="test-cookbook",
            output_type=output_type,
            status=status,
            files_generated=3,
            conversion_data=sample_conversion_data,
        )

        assert conversion_id is not None

        history = storage_manager.get_conversion_history(limit=1)
        assert history[0].output_type == output_type
        assert history[0].status == status

    @pytest.mark.parametrize("limit", [1, 10, 50, 100])
    def test_get_analysis_history_various_limits(
        self,
        storage_manager: StorageManager,
        limit: int,
        sample_analysis_data: dict[str, Any],
    ) -> None:
        """Test get_analysis_history with various limits."""
        for i in range(5):
            storage_manager.save_analysis(
                cookbook_name=f"cookbook-{i}",
                cookbook_path=f"/path{i}",
                cookbook_version="1.0.0",
                complexity="high",
                estimated_hours=40.0,
                estimated_hours_with_souschef=10.0,
                recommendations="Test",
                analysis_data=sample_analysis_data,
            )

        result = storage_manager.get_analysis_history(limit=limit)
        assert len(result) <= limit
        assert len(result) <= 5
