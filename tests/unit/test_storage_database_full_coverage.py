"""Tests to raise storage database coverage."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import souschef.storage.database as storage_db


class TestRowConversion:
    """Tests for row conversion helpers."""

    def test_analysis_from_row_missing_optional(self) -> None:
        """It handles missing optional columns."""
        row = {
            "id": 1,
            "cookbook_name": "cb",
            "cookbook_path": "/tmp/cb",  # NOSONAR
            "cookbook_version": "1.0",
            "complexity": "low",
            "estimated_hours": 1.0,
            "estimated_hours_with_souschef": 0.5,
            "recommendations": "ok",
            "ai_provider": None,
            "ai_model": None,
            "analysis_data": "{}",
            "created_at": "now",
            "cache_key": None,
        }
        result = storage_db._analysis_from_row(row)
        assert result.cookbook_blob_key is None
        assert result.content_fingerprint is None

    def test_conversion_from_row(self) -> None:
        """It converts conversion rows into dataclasses."""
        row = {
            "id": 2,
            "analysis_id": 1,
            "cookbook_name": "cb",
            "output_type": "playbook",
            "status": "success",
            "files_generated": 1,
            "blob_storage_key": None,
            "conversion_data": "{}",
            "created_at": "now",
        }
        result = storage_db._conversion_from_row(row)
        assert result.status == "success"


class TestHashing:
    """Tests for hashing helpers."""

    def test_hash_directory_contents(self, tmp_path: Path) -> None:
        """It hashes metadata and recipe files."""
        (tmp_path / "metadata.rb").write_text("name 'cb'", encoding="utf-8")
        recipes_dir = tmp_path / "recipes"
        recipes_dir.mkdir()
        (recipes_dir / "default.rb").write_text("package 'vim'", encoding="utf-8")

        digest = storage_db._hash_directory_contents(tmp_path)
        assert isinstance(digest, str)
        assert len(digest) == 64

    def test_calculate_file_fingerprint(self, tmp_path: Path) -> None:
        """It hashes file contents."""
        file_path = tmp_path / "archive.tgz"
        file_path.write_bytes(b"data" * 10)
        digest = storage_db.calculate_file_fingerprint(file_path)
        assert isinstance(digest, str)
        assert len(digest) == 64


class TestStorageManagerPaths:
    """Tests for StorageManager path handling."""

    def test_get_default_db_path(self, monkeypatch, tmp_path: Path) -> None:
        """It ensures the default path stays within temp root."""
        monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
        manager = storage_db.StorageManager()
        assert str(manager.db_path).startswith(str(tmp_path))

    def test_close_handles_missing_db(self, tmp_path: Path) -> None:
        """It handles close when database is missing."""
        manager = storage_db.StorageManager(db_path=tmp_path / "missing.db")
        manager.close()


class TestStorageManagerConnections:
    """Tests for connection lifecycle paths."""

    def test_delete_analysis_handles_error(self, tmp_path: Path) -> None:
        """It returns False on SQLite errors when deleting analyses."""
        manager = storage_db.StorageManager(db_path=tmp_path / "db.sqlite")
        with patch.object(manager, "_connect", side_effect=sqlite3.Error):
            assert manager.delete_analysis(1) is False

    def test_delete_conversion_handles_error(self, tmp_path: Path) -> None:
        """It returns False on SQLite errors when deleting conversions."""
        manager = storage_db.StorageManager(db_path=tmp_path / "db.sqlite")
        with patch.object(manager, "_connect", side_effect=sqlite3.Error):
            assert manager.delete_conversion(1) is False

    def test_get_statistics_with_no_rows(self, tmp_path: Path) -> None:
        """It returns default statistics when tables are empty."""
        manager = storage_db.StorageManager(db_path=tmp_path / "db.sqlite")
        stats = manager.get_statistics()
        assert stats["total_analyses"] == 0
        assert stats["total_conversions"] == 0


class TestPostgresStorageManager:
    """Tests for PostgreSQL manager helpers."""

    def test_get_psycopg_missing(self) -> None:
        """It raises a helpful error when psycopg is missing."""
        manager = storage_db.PostgresStorageManager.__new__(
            storage_db.PostgresStorageManager
        )
        with (
            patch("importlib.import_module", side_effect=ImportError("no")),
            pytest.raises(ImportError, match="psycopg is required"),
        ):
            manager._get_psycopg()

    def test_prepare_sql(self) -> None:
        """It replaces SQLite placeholders with PostgreSQL placeholders."""
        manager = storage_db.PostgresStorageManager.__new__(
            storage_db.PostgresStorageManager
        )
        assert manager._prepare_sql("SELECT * FROM t WHERE id = ?") == (
            "SELECT * FROM t WHERE id = %s"
        )

    def test_save_analysis_deduplication(self) -> None:
        """It returns existing IDs when fingerprints match."""
        manager = storage_db.PostgresStorageManager.__new__(
            storage_db.PostgresStorageManager
        )
        manager.get_analysis_by_fingerprint = MagicMock(
            return_value=SimpleNamespace(id=42)
        )
        manager.generate_cache_key = MagicMock(return_value="cache")
        result = storage_db.PostgresStorageManager.save_analysis(
            manager,
            cookbook_name="cb",
            cookbook_path="/tmp/cb",  # NOSONAR
            cookbook_version="1.0",
            complexity="low",
            estimated_hours=1.0,
            estimated_hours_with_souschef=0.5,
            recommendations="ok",
            analysis_data={},
            content_fingerprint="abc",
        )
        assert result == 42

    def test_get_analysis_by_fingerprint_none(self) -> None:
        """It returns None when no rows are found."""
        manager = storage_db.PostgresStorageManager.__new__(
            storage_db.PostgresStorageManager
        )

        class DummyConn:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

            def execute(self, *_args, **_kwargs):
                return SimpleNamespace(fetchone=lambda: None)

        manager._connect = MagicMock(return_value=DummyConn())
        result = storage_db.PostgresStorageManager.get_analysis_by_fingerprint(
            manager, "abc"
        )
        assert result is None
