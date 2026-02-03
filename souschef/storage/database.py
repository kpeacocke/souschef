"""Database models and storage manager for SousChef."""

import contextlib
import gc
import hashlib
import importlib
import json
import sqlite3
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from souschef.core.path_utils import _ensure_within_base_path, _normalize_path
from souschef.storage.config import build_postgres_dsn, load_database_settings


@dataclass
class AnalysisResult:
    """Represents a cookbook analysis result."""

    id: int | None
    cookbook_name: str
    cookbook_path: str
    cookbook_version: str
    complexity: str
    estimated_hours: float
    estimated_hours_with_souschef: float
    recommendations: str
    ai_provider: str | None
    ai_model: str | None
    analysis_data: str  # JSON
    created_at: str
    cache_key: str | None = None
    cookbook_blob_key: str | None = None  # Blob storage key for original cookbook
    content_fingerprint: str | None = None  # SHA256 hash of cookbook content


@dataclass
class ConversionResult:
    """Represents a cookbook conversion result."""

    id: int | None
    analysis_id: int | None
    cookbook_name: str
    output_type: str  # 'playbook', 'role', 'collection'
    status: str  # 'success', 'partial', 'failed'
    files_generated: int
    blob_storage_key: str | None
    conversion_data: str  # JSON
    created_at: str


def _analysis_from_row(row: Mapping[str, Any]) -> AnalysisResult:
    """Convert a database row into an AnalysisResult."""

    # Helper to safely get optional columns
    def safe_get(key: str) -> Any:
        if isinstance(row, dict):
            return row.get(key)
        try:
            return row[key]
        except (KeyError, IndexError):
            return None

    return AnalysisResult(
        id=row["id"],
        cookbook_name=row["cookbook_name"],
        cookbook_path=row["cookbook_path"],
        cookbook_version=row["cookbook_version"],
        complexity=row["complexity"],
        estimated_hours=row["estimated_hours"],
        estimated_hours_with_souschef=row["estimated_hours_with_souschef"],
        recommendations=row["recommendations"],
        ai_provider=row["ai_provider"],
        ai_model=row["ai_model"],
        analysis_data=row["analysis_data"],
        created_at=row["created_at"],
        cache_key=(row.get("cache_key") if isinstance(row, dict) else row["cache_key"]),
        cookbook_blob_key=safe_get("cookbook_blob_key"),
        content_fingerprint=safe_get("content_fingerprint"),
    )


def _conversion_from_row(row: Mapping[str, Any]) -> ConversionResult:
    """Convert a database row into a ConversionResult."""
    return ConversionResult(
        id=row["id"],
        analysis_id=row["analysis_id"],
        cookbook_name=row["cookbook_name"],
        output_type=row["output_type"],
        status=row["status"],
        files_generated=row["files_generated"],
        blob_storage_key=row["blob_storage_key"],
        conversion_data=row["conversion_data"],
        created_at=row["created_at"],
    )


def _hash_directory_contents(directory: Path) -> str:
    """Hash the contents of a directory for cache invalidation."""
    hasher = hashlib.sha256()

    key_files: list[Path] = [directory / "metadata.rb"]
    recipes_dir = directory / "recipes"
    if recipes_dir.exists():
        key_files.extend(sorted(recipes_dir.glob("*.rb")))

    for file_path in key_files:
        if file_path.exists() and file_path.is_file():
            hasher.update(file_path.read_bytes())

    return hasher.hexdigest()


def calculate_file_fingerprint(file_path: Path) -> str:
    """
    Calculate SHA256 fingerprint of a file.

    This is used for content-based deduplication of uploaded archives.

    Args:
        file_path: Path to the file to fingerprint.

    Returns:
        SHA256 hash of the file contents as hex string.

    """
    hasher = hashlib.sha256()
    with file_path.open("rb") as f:
        # Read in chunks to handle large files efficiently
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


class StorageManager:
    """Manages persistent storage for SousChef analysis and conversion data."""

    def __init__(self, db_path: str | Path | None = None):
        """
        Initialise the storage manager.

        Args:
            db_path: Path to SQLite database. If None, uses default location.

        """
        if db_path is None:
            db_path = self._get_default_db_path()
        else:
            db_path = _normalize_path(str(db_path))

        self.db_path = db_path
        self._ensure_database_exists()

    def __enter__(self) -> "StorageManager":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit with cleanup."""
        self.close()

    def close(self) -> None:
        """Close all database connections and ensure cleanup."""
        # Execute a dummy query to ensure all pending operations are complete
        # This helps prevent ResourceWarnings in tests
        if self.db_path.exists():
            conn = None
            try:
                conn = sqlite3.connect(str(self.db_path))
                conn.execute("SELECT 1")
                conn.commit()
            except Exception:
                pass
            finally:
                if conn is not None:
                    conn.close()

    @contextlib.contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Create a SQLite connection with proper cleanup."""
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.isolation_level = None
            yield conn
        finally:
            if conn is not None:
                try:
                    conn.execute("PRAGMA optimize")
                except Exception:
                    pass
                finally:
                    conn.close()

    def _get_default_db_path(self) -> Path:
        """Get the default database path in a secure location."""
        import tempfile

        # Use a data directory in temp for persistence across sessions
        data_dir = Path(tempfile.gettempdir()) / ".souschef" / "data"
        data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

        db_path = data_dir / "souschef.db"
        # Ensure the path is within the allowed base directory
        validated_path = _ensure_within_base_path(db_path, Path(tempfile.gettempdir()))
        return validated_path

    def _ensure_database_exists(self) -> None:
        """Create database schema if it doesn't exist."""
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS analysis_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cookbook_name TEXT NOT NULL,
                    cookbook_path TEXT NOT NULL,
                    cookbook_version TEXT,
                    complexity TEXT,
                    estimated_hours REAL,
                    estimated_hours_with_souschef REAL,
                    recommendations TEXT,
                    ai_provider TEXT,
                    ai_model TEXT,
                    analysis_data TEXT,
                    cache_key TEXT UNIQUE,
                    cookbook_blob_key TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Add cookbook_blob_key column if it doesn't exist (migration)
            with contextlib.suppress(sqlite3.OperationalError):
                conn.execute(
                    "ALTER TABLE analysis_results ADD COLUMN cookbook_blob_key TEXT"
                )

            # Add content_fingerprint column if it doesn't exist (migration)
            with contextlib.suppress(sqlite3.OperationalError):
                conn.execute(
                    "ALTER TABLE analysis_results ADD COLUMN content_fingerprint TEXT"
                )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversion_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_id INTEGER,
                    cookbook_name TEXT NOT NULL,
                    output_type TEXT,
                    status TEXT,
                    files_generated INTEGER,
                    blob_storage_key TEXT,
                    conversion_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (analysis_id) REFERENCES analysis_results (id)
                )
            """
            )

            # Create indexes for common queries
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_analysis_cookbook
                ON analysis_results(cookbook_name, created_at DESC)
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_analysis_cache
                ON analysis_results(cache_key)
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_analysis_fingerprint
                ON analysis_results(content_fingerprint)
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_conversion_analysis
                ON conversion_results(analysis_id)
            """
            )
        # Close connection explicitly after schema creation
        gc.collect()

    def generate_cache_key(
        self,
        cookbook_path: str,
        ai_provider: str | None = None,
        ai_model: str | None = None,
    ) -> str:
        """
        Generate a cache key for analysis results.

        Args:
            cookbook_path: Path to the cookbook.
            ai_provider: AI provider used (if any).
            ai_model: AI model used (if any).

        Returns:
            Cache key as a hex string.

        """
        # Include cookbook path, AI settings, and content hash
        key_parts = [
            cookbook_path,
            ai_provider or "none",
            ai_model or "none",
        ]

        # Try to include a hash of the cookbook content for invalidation
        try:
            cookbook_dir = _normalize_path(cookbook_path)
            content_hash = self._hash_directory_contents(cookbook_dir)
            key_parts.append(content_hash)
        except (ValueError, OSError):
            pass

        combined = "|".join(key_parts)
        return hashlib.sha256(combined.encode()).hexdigest()

    def _hash_directory_contents(self, directory: Path) -> str:
        """
        Hash the contents of a directory for cache invalidation.

        Args:
            directory: Directory to hash.

        Returns:
            SHA256 hash of directory contents.

        """
        return _hash_directory_contents(directory)

    def save_analysis(
        self,
        cookbook_name: str,
        cookbook_path: str,
        cookbook_version: str,
        complexity: str,
        estimated_hours: float,
        estimated_hours_with_souschef: float,
        recommendations: str,
        analysis_data: dict[str, Any],
        ai_provider: str | None = None,
        ai_model: str | None = None,
        cookbook_blob_key: str | None = None,
        content_fingerprint: str | None = None,
    ) -> int | None:
        """
        Save an analysis result to the database.

        If content_fingerprint is provided, checks for existing analysis with same
        fingerprint and returns existing ID instead of creating duplicate.

        Args:
            cookbook_name: Name of the cookbook.
            cookbook_path: Path to the cookbook.
            cookbook_version: Version of the cookbook.
            complexity: Complexity level.
            estimated_hours: Manual migration hours.
            estimated_hours_with_souschef: AI-assisted hours.
            recommendations: Analysis recommendations.
            analysis_data: Full analysis data as dict.
            ai_provider: AI provider used.
            ai_model: AI model used.
            cookbook_blob_key: Blob storage key for original cookbook archive.
            content_fingerprint: SHA256 hash of cookbook content for deduplication.

        Returns:
            The ID of the saved or existing analysis result.

        """
        # Check for existing analysis with same fingerprint
        if content_fingerprint:
            existing = self.get_analysis_by_fingerprint(content_fingerprint)
            if existing:
                # Return existing analysis ID (deduplication)
                return existing.id

        cache_key = self.generate_cache_key(cookbook_path, ai_provider, ai_model)

        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO analysis_results (
                    cookbook_name, cookbook_path, cookbook_version,
                    complexity, estimated_hours, estimated_hours_with_souschef,
                    recommendations, ai_provider, ai_model,
                    analysis_data, cache_key, cookbook_blob_key,
                    content_fingerprint
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    cookbook_name,
                    cookbook_path,
                    cookbook_version,
                    complexity,
                    estimated_hours,
                    estimated_hours_with_souschef,
                    recommendations,
                    ai_provider,
                    ai_model,
                    json.dumps(analysis_data),
                    cache_key,
                    cookbook_blob_key,
                    content_fingerprint,
                ),
            )
            conn.commit()
            return cursor.lastrowid or None

    def get_analysis_by_fingerprint(
        self, content_fingerprint: str
    ) -> AnalysisResult | None:
        """
        Retrieve existing analysis result by content fingerprint.

        Used for deduplication - if cookbook with same content was already
        uploaded, returns the existing analysis instead of creating duplicate.

        Args:
            content_fingerprint: SHA256 hash of cookbook content.

        Returns:
            Existing AnalysisResult or None if not found.

        """
        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM analysis_results
                WHERE content_fingerprint = ?
                ORDER BY created_at DESC
                LIMIT 1
            """,
                (content_fingerprint,),
            )
            row = cursor.fetchone()

            if row:
                return _analysis_from_row(row)

            return None

    def get_cached_analysis(
        self,
        cookbook_path: str,
        ai_provider: str | None = None,
        ai_model: str | None = None,
    ) -> AnalysisResult | None:
        """
        Retrieve cached analysis result if available.

        Args:
            cookbook_path: Path to the cookbook.
            ai_provider: AI provider used.
            ai_model: AI model used.

        Returns:
            Cached AnalysisResult or None if not found.

        """
        cache_key = self.generate_cache_key(cookbook_path, ai_provider, ai_model)

        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM analysis_results
                WHERE cache_key = ?
                ORDER BY created_at DESC
                LIMIT 1
            """,
                (cache_key,),
            )
            row = cursor.fetchone()

            if row:
                return AnalysisResult(
                    id=row["id"],
                    cookbook_name=row["cookbook_name"],
                    cookbook_path=row["cookbook_path"],
                    cookbook_version=row["cookbook_version"],
                    complexity=row["complexity"],
                    estimated_hours=row["estimated_hours"],
                    estimated_hours_with_souschef=row["estimated_hours_with_souschef"],
                    recommendations=row["recommendations"],
                    ai_provider=row["ai_provider"],
                    ai_model=row["ai_model"],
                    analysis_data=row["analysis_data"],
                    created_at=row["created_at"],
                    cache_key=row["cache_key"],
                )

        return None

    def save_conversion(
        self,
        cookbook_name: str,
        output_type: str,
        status: str,
        files_generated: int,
        conversion_data: dict[str, Any],
        analysis_id: int | None = None,
        blob_storage_key: str | None = None,
    ) -> int | None:
        """
        Save a conversion result to the database.

        Args:
            cookbook_name: Name of the cookbook.
            output_type: Output type (playbook, role, collection).
            status: Conversion status (success, partial, failed).
            files_generated: Number of files generated.
            conversion_data: Full conversion data as dict.
            analysis_id: Optional ID of associated analysis.
            blob_storage_key: Optional key for blob storage.

        Returns:
            The ID of the saved conversion result.

        """
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO conversion_results (
                    analysis_id, cookbook_name, output_type,
                    status, files_generated, blob_storage_key,
                    conversion_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    analysis_id,
                    cookbook_name,
                    output_type,
                    status,
                    files_generated,
                    blob_storage_key,
                    json.dumps(conversion_data),
                ),
            )
            conn.commit()
            return cursor.lastrowid or None

    def get_analysis_history(
        self, cookbook_name: str | None = None, limit: int = 50
    ) -> list[AnalysisResult]:
        """
        Get analysis history.

        Args:
            cookbook_name: Filter by cookbook name (optional).
            limit: Maximum number of results to return.

        Returns:
            List of AnalysisResult objects.

        """
        with self._connect() as conn:
            if cookbook_name:
                cursor = conn.execute(
                    """
                    SELECT * FROM analysis_results
                    WHERE cookbook_name = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """,
                    (cookbook_name, limit),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT * FROM analysis_results
                    ORDER BY created_at DESC
                    LIMIT ?
                """,
                    (limit,),
                )

            rows = cursor.fetchall()
            return [_analysis_from_row(row) for row in rows]

    def get_conversion_history(
        self, cookbook_name: str | None = None, limit: int = 50
    ) -> list[ConversionResult]:
        """
        Get conversion history.

        Args:
            cookbook_name: Filter by cookbook name (optional).
            limit: Maximum number of results to return.

        Returns:
            List of ConversionResult objects.

        """
        with self._connect() as conn:
            if cookbook_name:
                cursor = conn.execute(
                    """
                    SELECT * FROM conversion_results
                    WHERE cookbook_name = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """,
                    (cookbook_name, limit),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT * FROM conversion_results
                    ORDER BY created_at DESC
                    LIMIT ?
                """,
                    (limit,),
                )

            rows = cursor.fetchall()
            return [_conversion_from_row(row) for row in rows]

    def get_conversions_by_analysis_id(
        self, analysis_id: int
    ) -> list[ConversionResult]:
        """
        Get conversions associated with a specific analysis.

        Args:
            analysis_id: ID of the analysis.

        Returns:
            List of ConversionResult objects.

        """
        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM conversion_results
                WHERE analysis_id = ?
                ORDER BY created_at DESC
            """,
                (analysis_id,),
            )
            rows = cursor.fetchall()
            return [_conversion_from_row(row) for row in rows]

    def get_statistics(self) -> dict[str, Any]:
        """
        Get overall statistics.

        Returns:
            Dictionary with statistical data.

        """
        with self._connect() as conn:
            stats: dict[str, Any] = {}

            # Analysis statistics
            cursor = conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    COUNT(DISTINCT cookbook_name) as unique_cookbooks,
                    AVG(estimated_hours) as avg_manual_hours,
                    AVG(estimated_hours_with_souschef) as avg_ai_hours
                FROM analysis_results
            """
            )
            row = cursor.fetchone()
            stats["total_analyses"] = row[0]
            stats["unique_cookbooks_analysed"] = row[1]
            stats["avg_manual_hours"] = row[2] or 0
            stats["avg_ai_hours"] = row[3] or 0

            # Conversion statistics
            cursor = conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
                    SUM(files_generated) as total_files
                FROM conversion_results
            """
            )
            row = cursor.fetchone()
            stats["total_conversions"] = row[0]
            stats["successful_conversions"] = row[1]
            stats["total_files_generated"] = row[2] or 0

            return stats


class PostgresStorageManager:
    """Manages persistent storage for SousChef in PostgreSQL."""

    def __init__(self, dsn: str):
        """
        Initialise the PostgreSQL storage manager.

        Args:
            dsn: PostgreSQL DSN string.

        """
        self.dsn = dsn
        self._ensure_database_exists()

    def _get_psycopg(self):
        """Import psycopg and return the module."""
        try:
            return importlib.import_module("psycopg")
        except ImportError as exc:
            raise ImportError(
                "psycopg is required for PostgreSQL storage. Install with: "
                "pip install psycopg[binary]"
            ) from exc

    def _connect(self):
        """Create a PostgreSQL connection with dict row factory."""
        psycopg = self._get_psycopg()
        return psycopg.connect(self.dsn, row_factory=psycopg.rows.dict_row)

    def _prepare_sql(self, sql: str) -> str:
        """Convert SQLite-style placeholders to PostgreSQL placeholders."""
        return sql.replace("?", "%s")

    def _ensure_database_exists(self) -> None:
        """Create PostgreSQL schema if it doesn't exist."""
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS analysis_results (
                    id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    cookbook_name TEXT NOT NULL,
                    cookbook_path TEXT NOT NULL,
                    cookbook_version TEXT,
                    complexity TEXT,
                    estimated_hours DOUBLE PRECISION,
                    estimated_hours_with_souschef DOUBLE PRECISION,
                    recommendations TEXT,
                    ai_provider TEXT,
                    ai_model TEXT,
                    analysis_data TEXT,
                    cache_key TEXT UNIQUE,
                    cookbook_blob_key TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Add cookbook_blob_key column if it doesn't exist (migration)
            try:
                conn.execute(
                    "ALTER TABLE analysis_results ADD COLUMN cookbook_blob_key TEXT"
                )
                conn.commit()
            except Exception:
                # Column already exists
                conn.rollback()

            # Add content_fingerprint column if it doesn't exist (migration)
            try:
                conn.execute(
                    "ALTER TABLE analysis_results ADD COLUMN content_fingerprint TEXT"
                )
                conn.commit()
            except Exception:
                # Column already exists
                conn.rollback()

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversion_results (
                    id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    analysis_id INTEGER,
                    cookbook_name TEXT NOT NULL,
                    output_type TEXT,
                    status TEXT,
                    files_generated INTEGER,
                    blob_storage_key TEXT,
                    conversion_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (analysis_id) REFERENCES analysis_results (id)
                )
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_analysis_cookbook
                ON analysis_results(cookbook_name, created_at DESC)
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_analysis_cache
                ON analysis_results(cache_key)
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_analysis_fingerprint
                ON analysis_results(content_fingerprint)
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_conversion_analysis
                ON conversion_results(analysis_id)
            """
            )

            conn.commit()

    def generate_cache_key(
        self,
        cookbook_path: str,
        ai_provider: str | None = None,
        ai_model: str | None = None,
    ) -> str:
        """Generate a cache key for analysis results."""
        key_parts = [
            cookbook_path,
            ai_provider or "none",
            ai_model or "none",
        ]

        try:
            cookbook_dir = _normalize_path(cookbook_path)
            content_hash = _hash_directory_contents(cookbook_dir)
            key_parts.append(content_hash)
        except (ValueError, OSError):
            pass

        combined = "|".join(key_parts)
        return hashlib.sha256(combined.encode()).hexdigest()

    def save_analysis(
        self,
        cookbook_name: str,
        cookbook_path: str,
        cookbook_version: str,
        complexity: str,
        estimated_hours: float,
        estimated_hours_with_souschef: float,
        recommendations: str,
        analysis_data: dict[str, Any],
        ai_provider: str | None = None,
        ai_model: str | None = None,
        cookbook_blob_key: str | None = None,
        content_fingerprint: str | None = None,
    ) -> int | None:
        """
        Save an analysis result to PostgreSQL.

        If content_fingerprint is provided, checks for existing analysis with same
        fingerprint and returns existing ID instead of creating duplicate.

        Args:
            cookbook_name: Name of the cookbook.
            cookbook_path: Path to the cookbook.
            cookbook_version: Version of the cookbook.
            complexity: Complexity level.
            estimated_hours: Manual migration hours.
            estimated_hours_with_souschef: AI-assisted hours.
            recommendations: Analysis recommendations.
            analysis_data: Full analysis data as dict.
            ai_provider: AI provider used.
            ai_model: AI model used.
            cookbook_blob_key: Blob storage key for original cookbook archive.
            content_fingerprint: SHA256 hash of cookbook content for deduplication.

        Returns:
            The ID of the saved or existing analysis result.

        """
        # Check for existing analysis with same fingerprint
        if content_fingerprint:
            existing = self.get_analysis_by_fingerprint(content_fingerprint)
            if existing:
                # Return existing analysis ID (deduplication)
                return existing.id

        cache_key = self.generate_cache_key(cookbook_path, ai_provider, ai_model)

        sql = self._prepare_sql(
            """
            INSERT INTO analysis_results (
                cookbook_name, cookbook_path, cookbook_version,
                complexity, estimated_hours, estimated_hours_with_souschef,
                recommendations, ai_provider, ai_model,
                analysis_data, cache_key, cookbook_blob_key,
                content_fingerprint
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
        """
        )

        with self._connect() as conn:
            cursor = conn.execute(
                sql,
                (
                    cookbook_name,
                    cookbook_path,
                    cookbook_version,
                    complexity,
                    estimated_hours,
                    estimated_hours_with_souschef,
                    recommendations,
                    ai_provider,
                    ai_model,
                    json.dumps(analysis_data),
                    cache_key,
                    cookbook_blob_key,
                    content_fingerprint,
                ),
            )
            row = cursor.fetchone()
            conn.commit()
            if row:
                return int(row["id"])
            return None

    def get_analysis_by_fingerprint(
        self, content_fingerprint: str
    ) -> AnalysisResult | None:
        """
        Retrieve existing analysis result by content fingerprint.

        Used for deduplication - if cookbook with same content was already
        uploaded, returns the existing analysis instead of creating duplicate.

        Args:
            content_fingerprint: SHA256 hash of cookbook content.

        Returns:
            Existing AnalysisResult or None if not found.

        """
        sql = self._prepare_sql(
            """
            SELECT * FROM analysis_results
            WHERE content_fingerprint = ?
            ORDER BY created_at DESC
            LIMIT 1
        """
        )

        with self._connect() as conn:
            cursor = conn.execute(sql, (content_fingerprint,))
            row = cursor.fetchone()
            if row:
                return _analysis_from_row(row)
        return None

    def get_cached_analysis(
        self,
        cookbook_path: str,
        ai_provider: str | None = None,
        ai_model: str | None = None,
    ) -> AnalysisResult | None:
        """Retrieve cached analysis result if available."""
        cache_key = self.generate_cache_key(cookbook_path, ai_provider, ai_model)

        sql = self._prepare_sql(
            """
            SELECT * FROM analysis_results
            WHERE cache_key = ?
            ORDER BY created_at DESC
            LIMIT 1
        """
        )

        with self._connect() as conn:
            cursor = conn.execute(sql, (cache_key,))
            row = cursor.fetchone()
            if row:
                return _analysis_from_row(row)
        return None

    def save_conversion(
        self,
        cookbook_name: str,
        output_type: str,
        status: str,
        files_generated: int,
        conversion_data: dict[str, Any],
        analysis_id: int | None = None,
        blob_storage_key: str | None = None,
    ) -> int | None:
        """Save a conversion result to PostgreSQL."""
        sql = self._prepare_sql(
            """
            INSERT INTO conversion_results (
                analysis_id, cookbook_name, output_type,
                status, files_generated, blob_storage_key,
                conversion_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            RETURNING id
        """
        )

        with self._connect() as conn:
            cursor = conn.execute(
                sql,
                (
                    analysis_id,
                    cookbook_name,
                    output_type,
                    status,
                    files_generated,
                    blob_storage_key,
                    json.dumps(conversion_data),
                ),
            )
            row = cursor.fetchone()
            conn.commit()
            if row:
                return int(row["id"])
            return None

    def get_analysis_history(
        self, cookbook_name: str | None = None, limit: int = 50
    ) -> list[AnalysisResult]:
        """Get analysis history from PostgreSQL."""
        if cookbook_name:
            sql = self._prepare_sql(
                """
                SELECT * FROM analysis_results
                WHERE cookbook_name = ?
                ORDER BY created_at DESC
                LIMIT ?
            """
            )
            params: tuple[str | int, ...] = (cookbook_name, limit)
        else:
            sql = self._prepare_sql(
                """
                SELECT * FROM analysis_results
                ORDER BY created_at DESC
                LIMIT ?
            """
            )
            params = (limit,)

        with self._connect() as conn:
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()
            return [_analysis_from_row(row) for row in rows]

    def get_conversion_history(
        self, cookbook_name: str | None = None, limit: int = 50
    ) -> list[ConversionResult]:
        """Get conversion history from PostgreSQL."""
        if cookbook_name:
            sql = self._prepare_sql(
                """
                SELECT * FROM conversion_results
                WHERE cookbook_name = ?
                ORDER BY created_at DESC
                LIMIT ?
            """
            )
            params: tuple[str | int, ...] = (cookbook_name, limit)
        else:
            sql = self._prepare_sql(
                """
                SELECT * FROM conversion_results
                ORDER BY created_at DESC
                LIMIT ?
            """
            )
            params = (limit,)

        with self._connect() as conn:
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()
            return [_conversion_from_row(row) for row in rows]

    def get_conversions_by_analysis_id(
        self, analysis_id: int
    ) -> list[ConversionResult]:
        """
        Get all conversions for a specific analysis.

        Args:
            analysis_id: The ID of the analysis.

        Returns:
            List of conversion results for the analysis.

        """
        sql = self._prepare_sql(
            """
            SELECT * FROM conversion_results
            WHERE analysis_id = ?
            ORDER BY created_at DESC
        """
        )

        with self._connect() as conn:
            cursor = conn.execute(sql, (analysis_id,))
            rows = cursor.fetchall()
            return [_conversion_from_row(row) for row in rows]

    def get_statistics(self) -> dict[str, Any]:
        """Get overall statistics from PostgreSQL."""
        with self._connect() as conn:
            stats: dict[str, Any] = {}

            cursor = conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    COUNT(DISTINCT cookbook_name) as unique_cookbooks,
                    AVG(estimated_hours) as avg_manual_hours,
                    AVG(estimated_hours_with_souschef) as avg_ai_hours
                FROM analysis_results
            """
            )
            row = cursor.fetchone()
            stats["total_analyses"] = row["total"]
            stats["unique_cookbooks_analysed"] = row["unique_cookbooks"]
            stats["avg_manual_hours"] = row["avg_manual_hours"] or 0
            stats["avg_ai_hours"] = row["avg_ai_hours"] or 0

            cursor = conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
                    SUM(files_generated) as total_files
                FROM conversion_results
            """
            )
            row = cursor.fetchone()
            stats["total_conversions"] = row["total"]
            stats["successful_conversions"] = row["successful"]
            stats["total_files_generated"] = row["total_files"] or 0

            return stats


# Singleton instance
_storage_manager: StorageManager | PostgresStorageManager | None = None


def get_storage_manager() -> StorageManager | PostgresStorageManager:
    """
    Get or create the singleton StorageManager instance.

    Returns:
        StorageManager instance.

    """
    global _storage_manager
    settings = load_database_settings()

    if settings.backend == "postgres":
        if _storage_manager is None or not isinstance(
            _storage_manager, PostgresStorageManager
        ):
            _storage_manager = PostgresStorageManager(build_postgres_dsn(settings))
        return _storage_manager

    if _storage_manager is None or isinstance(_storage_manager, PostgresStorageManager):
        _storage_manager = StorageManager(db_path=settings.sqlite_path)
    return _storage_manager
