"""Additional tests for storage helpers."""

import importlib
import sqlite3
import tempfile
from collections.abc import Mapping
from pathlib import Path

import pytest

from souschef.storage import database
from souschef.storage.database import PostgresStorageManager, StorageManager


def test_analysis_from_row_handles_dict_optional_fields() -> None:
    """Test optional fields are read from dict rows."""
    row = {
        "id": 1,
        "cookbook_name": "app",
        "cookbook_path": "/tmp/app",  # NOSONAR
        "cookbook_version": "1.0.0",
        "complexity": "low",
        "estimated_hours": 10.0,
        "estimated_hours_with_souschef": 4.0,
        "recommendations": "ok",
        "ai_provider": "openai",
        "ai_model": "gpt",
        "analysis_data": "{}",
        "created_at": "2024-01-01",
        "cache_key": "cache",
        "cookbook_blob_key": "blob",
        "content_fingerprint": "fingerprint",
    }

    result = database._analysis_from_row(row)

    assert result.cookbook_blob_key == "blob"
    assert result.content_fingerprint == "fingerprint"


def test_analysis_from_row_handles_missing_optional_fields() -> None:
    """Test optional fields default to None for non-dict rows."""

    class MissingOptionalRow(Mapping[str, object]):
        def __init__(self, data: dict[str, object]) -> None:
            self._data = data

        def __getitem__(self, key: str) -> object:
            if key in self._data:
                return self._data[key]
            raise KeyError(key)

        def __iter__(self):
            return iter(self._data)

        def __len__(self) -> int:
            return len(self._data)

    row = MissingOptionalRow(
        {
            "id": 2,
            "cookbook_name": "service",
            "cookbook_path": "/tmp/service",  # NOSONAR
            "cookbook_version": "2.0.0",
            "complexity": "medium",
            "estimated_hours": 20.0,
            "estimated_hours_with_souschef": 8.0,
            "recommendations": "ok",
            "ai_provider": None,
            "ai_model": None,
            "analysis_data": "{}",
            "created_at": "2024-01-02",
            "cache_key": "cache-2",
        }
    )

    result = database._analysis_from_row(row)

    assert result.cookbook_blob_key is None
    assert result.content_fingerprint is None


def test_hash_directory_contents_changes_on_edit() -> None:
    """Test directory hash changes when a key file changes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cookbook_path = Path(tmpdir)
        (cookbook_path / "metadata.rb").write_text("name 'app'", encoding="utf-8")
        recipes_dir = cookbook_path / "recipes"
        recipes_dir.mkdir()
        recipe_path = recipes_dir / "default.rb"
        recipe_path.write_text("package 'vim'", encoding="utf-8")

        first_hash = database._hash_directory_contents(cookbook_path)
        recipe_path.write_text("package 'curl'", encoding="utf-8")
        second_hash = database._hash_directory_contents(cookbook_path)

        assert first_hash != second_hash


def test_calculate_file_fingerprint_changes() -> None:
    """Test file fingerprint changes when content changes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "archive.zip"
        file_path.write_bytes(b"first")

        first_hash = database.calculate_file_fingerprint(file_path)
        file_path.write_bytes(b"second")
        second_hash = database.calculate_file_fingerprint(file_path)

        assert first_hash != second_hash


def test_generate_cache_key_handles_invalid_path() -> None:
    """Test cache key generation tolerates invalid paths."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = StorageManager(db_path=Path(tmpdir) / "test.db")

        cache_key = manager.generate_cache_key("bad\x00path")

        assert isinstance(cache_key, str)
        assert len(cache_key) == 64


def test_delete_nonexistent_records_returns_false() -> None:
    """Test deletion returns False when records are missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = StorageManager(db_path=Path(tmpdir) / "test.db")

        assert manager.delete_analysis(9999) is False
        assert manager.delete_conversion(9999) is False


def test_postgres_prepare_sql_converts_placeholders() -> None:
    """Test PostgreSQL placeholder conversion."""
    manager = PostgresStorageManager.__new__(PostgresStorageManager)

    assert manager._prepare_sql("SELECT * FROM table WHERE id = ?") == (
        "SELECT * FROM table WHERE id = %s"
    )


def test_postgres_get_psycopg_requires_dependency(monkeypatch) -> None:
    """Test psycopg import error message."""
    manager = PostgresStorageManager.__new__(PostgresStorageManager)

    def raise_import(name: str):
        raise ImportError("missing psycopg")

    monkeypatch.setattr(importlib, "import_module", raise_import)

    with pytest.raises(ImportError, match="psycopg is required"):
        manager._get_psycopg()


def test_storage_manager_close_ignores_connect_errors(monkeypatch) -> None:
    """Test close swallows connection failures safely."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = StorageManager(db_path=Path(tmpdir) / "test.db")

        def raise_connect(*_args, **_kwargs):
            raise RuntimeError("connect failed")

        monkeypatch.setattr(database.sqlite3, "connect", raise_connect)

        manager.close()


def test_connect_pragmas_failure_does_not_block_cleanup(monkeypatch) -> None:
    """Test PRAGMA optimise failures still close the connection."""

    class StubConnection:
        def __init__(self) -> None:
            self.closed = False
            self.row_factory = None
            self.isolation_level = None

        def execute(self, query: str):
            if query == "PRAGMA optimize":
                raise sqlite3.OperationalError("optimise failed")
            return None

        def close(self) -> None:
            self.closed = True

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = StorageManager(db_path=Path(tmpdir) / "test.db")
        holder: dict[str, StubConnection] = {}

        def connect_stub(*_args, **_kwargs):
            conn = StubConnection()
            holder["conn"] = conn
            return conn

        monkeypatch.setattr(database.sqlite3, "connect", connect_stub)

        with manager._connect() as conn:
            assert conn is holder["conn"]

        assert holder["conn"].closed is True
