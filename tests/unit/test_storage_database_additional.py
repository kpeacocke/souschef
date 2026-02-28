"""Additional tests for storage database helpers."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from souschef.storage.database import (
    PostgresStorageManager,
    StorageManager,
    _analysis_from_row,
    _conversion_from_row,
    _hash_directory_contents,
)


class _MissingKeyRow(Mapping[str, Any]):
    """Mapping-like object that raises on missing keys."""

    def __init__(self, values: dict[str, Any]) -> None:
        self._values = values

    def __getitem__(self, key: str) -> Any:
        if key in self._values:
            return self._values[key]
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)


class _FakeConn:
    """Fake sqlite connection to exercise cleanup paths."""

    def __init__(self, fail_optimize: bool = False) -> None:
        self.fail_optimize = fail_optimize
        self.closed = False

    def execute(self, sql: str, params: tuple[Any, ...] | None = None) -> None:
        if self.fail_optimize and sql.strip().startswith("PRAGMA optimize"):
            raise sqlite3.Error("optimise failed")
        return None

    def close(self) -> None:
        self.closed = True


class _FakePsycopg:
    """Fake psycopg module for PostgresStorageManager tests."""

    class Rows:
        """Mimic psycopg.rows namespace."""

        dict_row = object()

    rows = Rows()

    def __init__(self, connection: MagicMock) -> None:
        self._connection = connection

    def connect(self, *_args: Any, **_kwargs: Any) -> MagicMock:
        return self._connection


def _fake_postgres_connection() -> MagicMock:
    conn = MagicMock()
    conn.__enter__.return_value = conn
    conn.__exit__.return_value = None
    return conn


class TestStorageDatabaseHelpers:
    """Cover storage database helper edge cases."""

    def test_analysis_from_row_handles_missing_optional_keys(self) -> None:
        """Ensure missing optional keys return None in analysis model."""
        row = _MissingKeyRow(
            {
                "id": 1,
                "cookbook_name": "test",
                "cookbook_path": "/tmp/cookbook",
                "cookbook_version": "1.0.0",
                "complexity": "low",
                "estimated_hours": 1.0,
                "estimated_hours_with_souschef": 0.5,
                "recommendations": "none",
                "ai_provider": None,
                "ai_model": None,
                "analysis_data": "{}",
                "created_at": "now",
                "cache_key": "cache",
            }
        )

        result = _analysis_from_row(row)

        assert result.cookbook_blob_key is None
        assert result.content_fingerprint is None

    def test_analysis_from_row_dict_uses_cache_key_get(self) -> None:
        """Ensure dict rows use get for cache key resolution."""
        row = {
            "id": 1,
            "cookbook_name": "test",
            "cookbook_path": "/tmp/cookbook",
            "cookbook_version": "1.0.0",
            "complexity": "low",
            "estimated_hours": 1.0,
            "estimated_hours_with_souschef": 0.5,
            "recommendations": "none",
            "ai_provider": None,
            "ai_model": None,
            "analysis_data": "{}",
            "created_at": "now",
        }

        result = _analysis_from_row(row)

        assert result.cache_key is None

    def test_hash_directory_contents_includes_recipes(self, tmp_path: Path) -> None:
        """Recipe files should be included in directory hashing."""
        (tmp_path / "metadata.rb").write_text("name 'test'")
        recipes_dir = tmp_path / "recipes"
        recipes_dir.mkdir()
        (recipes_dir / "default.rb").write_text("package 'nginx'")

        digest = _hash_directory_contents(tmp_path)

        assert isinstance(digest, str)
        assert len(digest) == 64

    def test_hash_directory_contents_handles_missing_recipes(
        self, tmp_path: Path
    ) -> None:
        """Hash should succeed even if recipes directory is missing."""
        (tmp_path / "metadata.rb").write_text("name 'test'")

        digest = _hash_directory_contents(tmp_path)

        assert isinstance(digest, str)
        assert len(digest) == 64

    def test_generate_cache_key_uses_directory_hash(self, tmp_path: Path) -> None:
        """Cache key should include directory hash when possible."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        manager = StorageManager(db_path=tmp_path / "test.db")
        key = manager.generate_cache_key(str(cookbook_dir), None, None)

        assert isinstance(key, str)
        assert len(key) == 64

    def test_conversion_from_row(self) -> None:
        """Conversion rows should map to ConversionResult."""
        row = {
            "id": 1,
            "analysis_id": 2,
            "cookbook_name": "cookbook",
            "output_type": "playbook",
            "status": "success",
            "files_generated": 3,
            "blob_storage_key": "blob",
            "conversion_data": "{}",
            "created_at": "now",
        }

        result = _conversion_from_row(row)

        assert result.status == "success"
        assert result.files_generated == 3

    def test_get_default_db_path(self) -> None:
        """Default DB path should be resolvable."""
        manager = StorageManager.__new__(StorageManager)
        default_path = manager._get_default_db_path()

        assert isinstance(default_path, Path)

    def test_get_history_and_statistics(self, tmp_path: Path) -> None:
        """History and statistics should return values from SQLite DB."""
        manager = StorageManager(db_path=tmp_path / "test.db")

        analysis_id = manager.save_analysis(
            cookbook_name="cookbook",
            cookbook_path="/tmp/cookbook",
            cookbook_version="1.0.0",
            complexity="low",
            estimated_hours=1.0,
            estimated_hours_with_souschef=0.5,
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

        assert conversion_id is not None

        history = manager.get_analysis_history()
        assert len(history) == 1

        filtered_history = manager.get_analysis_history(cookbook_name="cookbook")
        assert len(filtered_history) == 1

        conversions = manager.get_conversion_history()
        assert len(conversions) == 1

        filtered_conversions = manager.get_conversion_history(cookbook_name="cookbook")
        assert len(filtered_conversions) == 1

        by_analysis = manager.get_conversions_by_analysis_id(analysis_id or 0)
        assert len(by_analysis) == 1

        stats = manager.get_statistics()
        assert stats["total_analyses"] == 1
        assert stats["total_conversions"] == 1

        assert manager.delete_conversion(conversion_id or 0) is True
        assert manager.delete_analysis(analysis_id or 0) is True

    def test_storage_close_handles_sqlite_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Close should swallow sqlite errors during best-effort cleanup."""
        db_path = tmp_path / "test.db"
        manager = StorageManager(db_path=db_path)

        def _raise_connect(_path: str) -> None:
            raise sqlite3.Error("connect failed")

        monkeypatch.setattr(sqlite3, "connect", _raise_connect)
        manager.close()

    def test_connect_pragmas_error_is_handled(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Optimisation errors should not leak during connection cleanup."""
        db_path = tmp_path / "test.db"
        manager = StorageManager(db_path=db_path)

        fake_conn = _FakeConn(fail_optimize=True)

        def _connect(_path: str, check_same_thread: bool = False) -> _FakeConn:
            return fake_conn

        monkeypatch.setattr(sqlite3, "connect", _connect)

        with manager._connect():
            # Exercise the context manager
            assert fake_conn.closed is False

        assert fake_conn.closed is True

    def test_delete_analysis_handles_sqlite_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Delete analysis should return None on database errors."""
        manager = StorageManager(db_path=tmp_path / "test.db")

        class _BadContext:
            def __enter__(self) -> None:
                raise sqlite3.Error("db failure")

            def __exit__(self, _exc_type, _exc, _tb) -> None:
                return None

        monkeypatch.setattr(manager, "_connect", lambda: _BadContext())

        assert manager.delete_analysis(1) is False

    def test_delete_conversion_handles_sqlite_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Delete conversion should return None on database errors."""
        manager = StorageManager(db_path=tmp_path / "test.db")

        class _BadContext:
            def __enter__(self) -> None:
                raise sqlite3.Error("db failure")

            def __exit__(self, _exc_type, _exc, _tb) -> None:
                return None

        monkeypatch.setattr(manager, "_connect", lambda: _BadContext())

        assert manager.delete_conversion(1) is False


class TestPostgresStorageManager:
    """Tests for PostgreSQL storage manager paths."""

    def test_get_psycopg_import_error(self) -> None:
        """Import error should raise with helpful message."""
        manager = PostgresStorageManager.__new__(PostgresStorageManager)
        manager.dsn = "postgresql://example"

        with patch("importlib.import_module") as mock_import:
            mock_import.side_effect = ImportError("No module named 'psycopg'")

            with pytest.raises(ImportError, match="psycopg is required"):
                manager._get_psycopg()

    def test_prepare_sql_replaces_placeholders(self) -> None:
        """Prepare should convert sqlite placeholders."""
        manager = PostgresStorageManager.__new__(PostgresStorageManager)
        manager.dsn = "postgresql://example"

        assert (
            manager._prepare_sql("SELECT * FROM t WHERE id = ?")
            == "SELECT * FROM t WHERE id = %s"
        )

    def test_ensure_database_exists_rolls_back(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Schema creation should rollback on migration conflicts."""
        conn = _fake_postgres_connection()

        def _execute(sql: str, _params: tuple[Any, ...] | None = None) -> MagicMock:
            if sql.strip().startswith("ALTER TABLE"):
                raise RuntimeError("already exists")
            return MagicMock()

        conn.execute.side_effect = _execute
        fake_psycopg = _FakePsycopg(conn)

        manager = PostgresStorageManager.__new__(PostgresStorageManager)
        manager.dsn = "postgresql://example"
        monkeypatch.setattr(manager, "_get_psycopg", lambda: fake_psycopg)

        manager._ensure_database_exists()

        assert conn.rollback.called

    def test_generate_cache_key_falls_back_on_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Hash errors should not break cache key generation."""
        manager = PostgresStorageManager.__new__(PostgresStorageManager)
        manager.dsn = "postgresql://example"

        def _raise_error(_value: str) -> str:
            raise ValueError("bad path")

        monkeypatch.setattr(
            "souschef.storage.database._normalize_path",
            _raise_error,
        )

        key = manager.generate_cache_key("/invalid", None, None)

        assert isinstance(key, str)
        assert len(key) == 64

    def test_save_analysis_returns_existing_id(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Deduplication should return existing analysis id."""
        manager = PostgresStorageManager.__new__(PostgresStorageManager)
        manager.dsn = "postgresql://example"
        monkeypatch.setattr(
            manager,
            "get_analysis_by_fingerprint",
            lambda _fp: type("Result", (), {"id": 42})(),
        )

        result = manager.save_analysis(
            cookbook_name="test",
            cookbook_path="/tmp",
            cookbook_version="1.0.0",
            complexity="low",
            estimated_hours=1.0,
            estimated_hours_with_souschef=0.5,
            recommendations="",
            analysis_data={},
            content_fingerprint="abc",
        )

        assert result == 42

    def test_save_analysis_returns_none_when_no_row(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Save analysis should return None when insert returns no row."""
        conn = _fake_postgres_connection()
        conn.execute.return_value.fetchone.return_value = None
        fake_psycopg = _FakePsycopg(conn)

        manager = PostgresStorageManager.__new__(PostgresStorageManager)
        manager.dsn = "postgresql://example"
        monkeypatch.setattr(manager, "_get_psycopg", lambda: fake_psycopg)

        result = manager.save_analysis(
            cookbook_name="test",
            cookbook_path="/tmp",
            cookbook_version="1.0.0",
            complexity="low",
            estimated_hours=1.0,
            estimated_hours_with_souschef=0.5,
            recommendations="",
            analysis_data={},
        )

        assert result is None

    def test_save_conversion_returns_none_when_no_row(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Save conversion should return None when insert returns no row."""
        conn = _fake_postgres_connection()
        conn.execute.return_value.fetchone.return_value = None
        fake_psycopg = _FakePsycopg(conn)

        manager = PostgresStorageManager.__new__(PostgresStorageManager)
        manager.dsn = "postgresql://example"
        monkeypatch.setattr(manager, "_get_psycopg", lambda: fake_psycopg)

        result = manager.save_conversion(
            cookbook_name="cookbook",
            output_type="playbook",
            status="success",
            files_generated=1,
            conversion_data={},
        )

        assert result is None

    def test_history_and_statistics(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """History queries and statistics should return mapped results."""
        conn = _fake_postgres_connection()

        analysis_row = {
            "id": 1,
            "cookbook_name": "cookbook",
            "cookbook_path": "/tmp/cookbook",
            "cookbook_version": "1.0.0",
            "complexity": "low",
            "estimated_hours": 1.0,
            "estimated_hours_with_souschef": 0.5,
            "recommendations": "",
            "ai_provider": None,
            "ai_model": None,
            "analysis_data": "{}",
            "created_at": "now",
            "cache_key": "cache",
            "cookbook_blob_key": None,
            "content_fingerprint": None,
        }
        conversion_row = {
            "id": 1,
            "analysis_id": 1,
            "cookbook_name": "cookbook",
            "output_type": "playbook",
            "status": "success",
            "files_generated": 1,
            "blob_storage_key": None,
            "conversion_data": "{}",
            "created_at": "now",
        }

        def _fetchall():
            return [analysis_row]

        def _fetchall_conversion():
            return [conversion_row]

        def _execute(sql: str, _params: tuple[Any, ...] | None = None) -> MagicMock:
            cursor = MagicMock()
            if "conversion_results" in sql and "COUNT" not in sql:
                cursor.fetchall.return_value = _fetchall_conversion()
            elif "analysis_results" in sql and "COUNT" not in sql:
                cursor.fetchall.return_value = _fetchall()
            elif "COUNT" in sql and "analysis_results" in sql:
                cursor.fetchone.return_value = {
                    "total": 1,
                    "unique_cookbooks": 1,
                    "avg_manual_hours": 1.0,
                    "avg_ai_hours": 0.5,
                }
            elif "COUNT" in sql and "conversion_results" in sql:
                cursor.fetchone.return_value = {
                    "total": 1,
                    "successful": 1,
                    "total_files": 1,
                }
            return cursor

        conn.execute.side_effect = _execute
        fake_psycopg = _FakePsycopg(conn)

        manager = PostgresStorageManager.__new__(PostgresStorageManager)
        manager.dsn = "postgresql://example"
        monkeypatch.setattr(manager, "_get_psycopg", lambda: fake_psycopg)

        assert manager.get_analysis_history() != []
        assert manager.get_analysis_history(cookbook_name="cookbook") != []
        assert manager.get_conversion_history() != []
        assert manager.get_conversion_history(cookbook_name="cookbook") != []
        assert manager.get_conversions_by_analysis_id(1) != []

        stats = manager.get_statistics()
        assert stats["total_analyses"] == 1
        assert stats["total_conversions"] == 1

    def test_delete_analysis_handles_exception(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Delete analysis should handle connection errors gracefully."""
        conn = _fake_postgres_connection()
        conn.execute.side_effect = Exception("db error")
        fake_psycopg = _FakePsycopg(conn)

        manager = PostgresStorageManager.__new__(PostgresStorageManager)
        manager.dsn = "postgresql://example"
        monkeypatch.setattr(manager, "_get_psycopg", lambda: fake_psycopg)

        assert manager.delete_analysis(1) is False

    def test_delete_conversion_handles_exception(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Delete conversion should handle connection errors gracefully."""
        conn = _fake_postgres_connection()
        conn.execute.side_effect = Exception("db error")
        fake_psycopg = _FakePsycopg(conn)

        manager = PostgresStorageManager.__new__(PostgresStorageManager)
        manager.dsn = "postgresql://example"
        monkeypatch.setattr(manager, "_get_psycopg", lambda: fake_psycopg)

        assert manager.delete_conversion(1) is False
