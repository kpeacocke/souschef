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


@dataclass
class WorkspaceMembership:
    """Represents a user role assignment within a workspace."""

    workspace_id: str
    user_id: str
    role: str
    updated_by: str | None
    updated_at: str


@dataclass
class AuditEvent:
    """Represents an audit event for workspace-level actions."""

    id: int | None
    workspace_id: str
    user_id: str
    event_type: str
    action: str
    target_user_id: str | None
    details: str
    created_at: str


@dataclass
class ApprovalRequest:
    """Represents a workspace approval request and decision state."""

    id: int | None
    workspace_id: str
    action: str
    status: str
    requested_by: str
    target_user_id: str | None
    request_comment: str
    decision_comment: str | None
    details: str
    decided_by: str | None
    requested_at: str
    decided_at: str | None


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


def _membership_from_row(row: Mapping[str, Any]) -> WorkspaceMembership:
    """Convert a database row into a WorkspaceMembership."""
    return WorkspaceMembership(
        workspace_id=row["workspace_id"],
        user_id=row["user_id"],
        role=row["role"],
        updated_by=row["updated_by"],
        updated_at=row["updated_at"],
    )


def _audit_from_row(row: Mapping[str, Any]) -> AuditEvent:
    """Convert a database row into an AuditEvent."""
    return AuditEvent(
        id=row["id"],
        workspace_id=row["workspace_id"],
        user_id=row["user_id"],
        event_type=row["event_type"],
        action=row["action"],
        target_user_id=row["target_user_id"],
        details=row["details"],
        created_at=row["created_at"],
    )


def _approval_from_row(row: Mapping[str, Any]) -> ApprovalRequest:
    """Convert a database row into an ApprovalRequest."""
    return ApprovalRequest(
        id=row["id"],
        workspace_id=row["workspace_id"],
        action=row["action"],
        status=row["status"],
        requested_by=row["requested_by"],
        target_user_id=row["target_user_id"],
        request_comment=row["request_comment"],
        decision_comment=row["decision_comment"],
        details=row["details"],
        decided_by=row["decided_by"],
        requested_at=row["requested_at"],
        decided_at=row["decided_at"],
    )


def _hash_directory_contents(directory: Path) -> str:
    """Hash the contents of a directory for cache invalidation."""
    hasher = hashlib.sha256()

    key_files: list[Path] = [directory / "metadata.rb"]
    recipes_dir = directory / "recipes"
    if recipes_dir.exists():  # NOSONAR
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
        if self.db_path.exists():  # NOSONAR
            conn = None
            try:
                conn = sqlite3.connect(str(self.db_path))
                conn.execute("SELECT 1")
                conn.commit()
            except Exception:
                # Best-effort check; failure is non-fatal and retried later.
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
                    # Optimisation failure should not block cleanup.
                    pass
                finally:
                    conn.close()

    def _get_default_db_path(self) -> Path:
        """Get the default database path in a secure location."""
        import tempfile

        # Use a data directory in temp for persistence across sessions
        # Private temp subdirectory with restrictive permissions.
        # NOSONAR python:S5443
        data_dir = Path(tempfile.gettempdir()) / ".souschef" / "data"
        data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

        db_path = data_dir / "souschef.db"
        # Ensure the path is within the allowed base directory
        # Containment validation prevents unsafe path usage.
        # NOSONAR python:S5443
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

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workspace_memberships (
                    workspace_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    updated_by TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (workspace_id, user_id)
                )
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_workspace_memberships_workspace
                ON workspace_memberships(workspace_id)
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workspace_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    action TEXT NOT NULL,
                    target_user_id TEXT,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_audit_events_workspace
                ON audit_events(workspace_id, created_at DESC)
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS approval_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workspace_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    status TEXT NOT NULL,
                    requested_by TEXT NOT NULL,
                    target_user_id TEXT,
                    request_comment TEXT NOT NULL,
                    decision_comment TEXT,
                    details TEXT,
                    decided_by TEXT,
                    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    decided_at TIMESTAMP
                )
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_approval_requests_workspace
                ON approval_requests(workspace_id, requested_at DESC)
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_approval_requests_status
                ON approval_requests(workspace_id, status, requested_at DESC)
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
            # If the cookbook path is invalid or the contents cannot be read,
            # fall back to a cache key that does not include a content
            # fingerprint so caching still works, albeit with reduced
            # granularity.
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

    def delete_analysis(self, analysis_id: int) -> bool:
        """
        Delete an analysis result and its associated conversions.

        Args:
            analysis_id: ID of the analysis to delete.

        Returns:
            True if successful, False otherwise.

        """
        try:
            with self._connect() as conn:
                # First delete associated conversions
                conn.execute(
                    "DELETE FROM conversion_results WHERE analysis_id = ?",
                    (analysis_id,),
                )

                # Then delete the analysis
                cursor = conn.execute(
                    "DELETE FROM analysis_results WHERE id = ?", (analysis_id,)
                )

                return cursor.rowcount > 0
        except sqlite3.Error:
            # Database errors during deletion should not propagate to UI
            # Return False to indicate deletion failed gracefully
            return False

    def delete_conversion(self, conversion_id: int) -> bool:
        """
        Delete a conversion result.

        Args:
            conversion_id: ID of the conversion to delete.

        Returns:
            True if successful, False otherwise.

        """
        try:
            with self._connect() as conn:
                cursor = conn.execute(
                    "DELETE FROM conversion_results WHERE id = ?", (conversion_id,)
                )
                return cursor.rowcount > 0
        except sqlite3.Error:
            # Database errors during deletion should not propagate to UI
            # Return False to indicate deletion failed gracefully
            return False

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

    def upsert_workspace_role(
        self,
        workspace_id: str,
        user_id: str,
        role: str,
        updated_by: str | None = None,
    ) -> None:
        """Create or update a workspace role assignment for a user."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO workspace_memberships (
                    workspace_id, user_id, role, updated_by, updated_at
                ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(workspace_id, user_id)
                DO UPDATE SET
                    role = excluded.role,
                    updated_by = excluded.updated_by,
                    updated_at = CURRENT_TIMESTAMP
            """,
                (workspace_id, user_id, role, updated_by),
            )

    def get_workspace_role(self, workspace_id: str, user_id: str) -> str | None:
        """Get role for a user in a workspace, if assigned."""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT role FROM workspace_memberships
                WHERE workspace_id = ? AND user_id = ?
                LIMIT 1
            """,
                (workspace_id, user_id),
            )
            row = cursor.fetchone()
            if row:
                role_value = row["role"]
                if role_value is not None:
                    return str(role_value)
        return None

    def list_workspace_members(self, workspace_id: str) -> list[WorkspaceMembership]:
        """List all users and roles assigned to a workspace."""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT workspace_id, user_id, role, updated_by, updated_at
                FROM workspace_memberships
                WHERE workspace_id = ?
                ORDER BY updated_at DESC, user_id ASC
            """,
                (workspace_id,),
            )
            rows = cursor.fetchall()
            return [_membership_from_row(row) for row in rows]

    def count_workspace_members_with_role(self, workspace_id: str, role: str) -> int:
        """Count members in a workspace assigned to a specific role."""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM workspace_memberships
                WHERE workspace_id = ? AND role = ?
            """,
                (workspace_id, role),
            )
            row = cursor.fetchone()
            return int(row["count"]) if row else 0

    def remove_workspace_member(self, workspace_id: str, user_id: str) -> bool:
        """Remove a user role assignment from a workspace."""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                DELETE FROM workspace_memberships
                WHERE workspace_id = ? AND user_id = ?
            """,
                (workspace_id, user_id),
            )
            return bool(cursor.rowcount and cursor.rowcount > 0)

    def add_audit_event(
        self,
        workspace_id: str,
        user_id: str,
        event_type: str,
        action: str,
        target_user_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> int | None:
        """Persist an audit event and return its ID."""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO audit_events (
                    workspace_id, user_id, event_type, action, target_user_id, details
                ) VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    workspace_id,
                    user_id,
                    event_type,
                    action,
                    target_user_id,
                    json.dumps(details or {}),
                ),
            )
            return int(cursor.lastrowid) if cursor.lastrowid is not None else None

    def get_audit_events(self, workspace_id: str, limit: int = 100) -> list[AuditEvent]:
        """Get audit events for a workspace ordered newest-first."""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM audit_events
                WHERE workspace_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
            """,
                (workspace_id, limit),
            )
            rows = cursor.fetchall()
            return [_audit_from_row(row) for row in rows]

    def create_approval_request(
        self,
        workspace_id: str,
        action: str,
        requested_by: str,
        request_comment: str,
        target_user_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> int | None:
        """Create a pending approval request."""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO approval_requests (
                    workspace_id,
                    action,
                    status,
                    requested_by,
                    target_user_id,
                    request_comment,
                    details
                ) VALUES (?, ?, 'pending', ?, ?, ?, ?)
            """,
                (
                    workspace_id,
                    action,
                    requested_by,
                    target_user_id,
                    request_comment,
                    json.dumps(details or {}),
                ),
            )
            return int(cursor.lastrowid) if cursor.lastrowid is not None else None

    def get_approval_request(self, request_id: int) -> ApprovalRequest | None:
        """Get approval request by ID."""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM approval_requests
                WHERE id = ?
                LIMIT 1
            """,
                (request_id,),
            )
            row = cursor.fetchone()
            if row:
                return _approval_from_row(row)
        return None

    def list_approval_requests(
        self,
        workspace_id: str,
        status: str | None = None,
        limit: int = 100,
    ) -> list[ApprovalRequest]:
        """List approval requests for a workspace ordered newest-first."""
        with self._connect() as conn:
            if status:
                cursor = conn.execute(
                    """
                    SELECT * FROM approval_requests
                    WHERE workspace_id = ? AND status = ?
                    ORDER BY requested_at DESC, id DESC
                    LIMIT ?
                """,
                    (workspace_id, status, limit),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT * FROM approval_requests
                    WHERE workspace_id = ?
                    ORDER BY requested_at DESC, id DESC
                    LIMIT ?
                """,
                    (workspace_id, limit),
                )
            rows = cursor.fetchall()
            return [_approval_from_row(row) for row in rows]

    def decide_approval_request(
        self,
        request_id: int,
        decided_by: str,
        decision: str,
        decision_comment: str | None = None,
    ) -> ApprovalRequest | None:
        """Transition a pending approval request to approved or rejected."""
        decision_normalised = decision.strip().lower()
        if decision_normalised not in {"approved", "rejected"}:
            raise ValueError(f"Invalid decision: {decision}")

        current = self.get_approval_request(request_id)
        if current is None:
            return None
        if current.status != "pending":
            raise ValueError(
                f"Approval request {request_id} is already in state '{current.status}'"
            )

        with self._connect() as conn:
            conn.execute(
                """
                UPDATE approval_requests
                SET status = ?,
                    decision_comment = ?,
                    decided_by = ?,
                    decided_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """,
                (
                    decision_normalised,
                    decision_comment,
                    decided_by,
                    request_id,
                ),
            )
        return self.get_approval_request(request_id)


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
            conn.commit()

            # Add content_fingerprint column if it doesn't exist (migration)
            try:
                conn.execute(
                    "ALTER TABLE analysis_results ADD COLUMN content_fingerprint TEXT"
                )
                conn.commit()
            except Exception:
                # Column may already exist; rollback and continue
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
            conn.commit()

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

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workspace_memberships (
                    workspace_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    updated_by TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (workspace_id, user_id)
                )
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_workspace_memberships_workspace
                ON workspace_memberships(workspace_id)
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    workspace_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    action TEXT NOT NULL,
                    target_user_id TEXT,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_audit_events_workspace
                ON audit_events(workspace_id, created_at DESC)
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS approval_requests (
                    id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    workspace_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    status TEXT NOT NULL,
                    requested_by TEXT NOT NULL,
                    target_user_id TEXT,
                    request_comment TEXT NOT NULL,
                    decision_comment TEXT,
                    details TEXT,
                    decided_by TEXT,
                    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    decided_at TIMESTAMP
                )
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_approval_requests_workspace
                ON approval_requests(workspace_id, requested_at DESC)
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_approval_requests_status
                ON approval_requests(workspace_id, status, requested_at DESC)
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
        except (ValueError, OSError):  # pragma: no cover
            # Keep cache key stable even if hashing fails.
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

    def delete_analysis(self, analysis_id: int) -> bool:
        """
        Delete an analysis result and its associated conversions.

        Args:
            analysis_id: ID of the analysis to delete.

        Returns:
            True if successful, False otherwise.

        """
        try:
            with self._connect() as conn:
                # First delete associated conversions
                sql = self._prepare_sql(
                    "DELETE FROM conversion_results WHERE analysis_id = ?"
                )
                conn.execute(sql, (analysis_id,))

                # Then delete the analysis
                sql = self._prepare_sql("DELETE FROM analysis_results WHERE id = ?")
                cursor = conn.execute(sql, (analysis_id,))

                # Commit changes
                conn.commit()

                return bool(cursor.rowcount and cursor.rowcount > 0)
        except Exception:
            # Catch all database-related exceptions (psycopg errors, connection issues)
            # Return False to indicate deletion failed gracefully
            return False

    def delete_conversion(self, conversion_id: int) -> bool:
        """
        Delete a conversion result.

        Args:
            conversion_id: ID of the conversion to delete.

        Returns:
            True if successful, False otherwise.

        """
        try:
            with self._connect() as conn:
                sql = self._prepare_sql("DELETE FROM conversion_results WHERE id = ?")
                cursor = conn.execute(sql, (conversion_id,))
                conn.commit()
                return bool(cursor.rowcount and cursor.rowcount > 0)
        except Exception:
            # Catch all database-related exceptions (psycopg errors, connection issues)
            # Return False to indicate deletion failed gracefully
            return False

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

    def upsert_workspace_role(
        self,
        workspace_id: str,
        user_id: str,
        role: str,
        updated_by: str | None = None,
    ) -> None:
        """Create or update a workspace role assignment for a user."""
        sql = self._prepare_sql(
            """
            INSERT INTO workspace_memberships (
                workspace_id, user_id, role, updated_by, updated_at
            ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(workspace_id, user_id)
            DO UPDATE SET
                role = excluded.role,
                updated_by = excluded.updated_by,
                updated_at = CURRENT_TIMESTAMP
        """
        )
        with self._connect() as conn:
            conn.execute(sql, (workspace_id, user_id, role, updated_by))
            conn.commit()

    def get_workspace_role(self, workspace_id: str, user_id: str) -> str | None:
        """Get role for a user in a workspace, if assigned."""
        sql = self._prepare_sql(
            """
            SELECT role FROM workspace_memberships
            WHERE workspace_id = ? AND user_id = ?
            LIMIT 1
        """
        )
        with self._connect() as conn:
            cursor = conn.execute(sql, (workspace_id, user_id))
            row = cursor.fetchone()
            if row:
                role_value = row["role"]
                if role_value is not None:
                    return str(role_value)
        return None

    def list_workspace_members(self, workspace_id: str) -> list[WorkspaceMembership]:
        """List all users and roles assigned to a workspace."""
        sql = self._prepare_sql(
            """
            SELECT workspace_id, user_id, role, updated_by, updated_at
            FROM workspace_memberships
            WHERE workspace_id = ?
            ORDER BY updated_at DESC, user_id ASC
        """
        )
        with self._connect() as conn:
            cursor = conn.execute(sql, (workspace_id,))
            rows = cursor.fetchall()
            return [_membership_from_row(row) for row in rows]

    def count_workspace_members_with_role(self, workspace_id: str, role: str) -> int:
        """Count members in a workspace assigned to a specific role."""
        sql = self._prepare_sql(
            """
            SELECT COUNT(*) AS count
            FROM workspace_memberships
            WHERE workspace_id = ? AND role = ?
        """
        )
        with self._connect() as conn:
            cursor = conn.execute(sql, (workspace_id, role))
            row = cursor.fetchone()
            return int(row["count"]) if row else 0

    def remove_workspace_member(self, workspace_id: str, user_id: str) -> bool:
        """Remove a user role assignment from a workspace."""
        sql = self._prepare_sql(
            """
            DELETE FROM workspace_memberships
            WHERE workspace_id = ? AND user_id = ?
        """
        )
        with self._connect() as conn:
            cursor = conn.execute(sql, (workspace_id, user_id))
            conn.commit()
            return bool(cursor.rowcount and cursor.rowcount > 0)

    def add_audit_event(
        self,
        workspace_id: str,
        user_id: str,
        event_type: str,
        action: str,
        target_user_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> int | None:
        """Persist an audit event and return its ID."""
        sql = self._prepare_sql(
            """
            INSERT INTO audit_events (
                workspace_id, user_id, event_type, action, target_user_id, details
            ) VALUES (?, ?, ?, ?, ?, ?)
            RETURNING id
        """
        )
        with self._connect() as conn:
            cursor = conn.execute(
                sql,
                (
                    workspace_id,
                    user_id,
                    event_type,
                    action,
                    target_user_id,
                    json.dumps(details or {}),
                ),
            )
            row = cursor.fetchone()
            conn.commit()
            if row:
                return int(row["id"])
        return None

    def get_audit_events(self, workspace_id: str, limit: int = 100) -> list[AuditEvent]:
        """Get audit events for a workspace ordered newest-first."""
        sql = self._prepare_sql(
            """
            SELECT * FROM audit_events
            WHERE workspace_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
        """
        )
        with self._connect() as conn:
            cursor = conn.execute(sql, (workspace_id, limit))
            rows = cursor.fetchall()
            return [_audit_from_row(row) for row in rows]

    def create_approval_request(
        self,
        workspace_id: str,
        action: str,
        requested_by: str,
        request_comment: str,
        target_user_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> int | None:
        """Create a pending approval request."""
        sql = self._prepare_sql(
            """
            INSERT INTO approval_requests (
                workspace_id,
                action,
                status,
                requested_by,
                target_user_id,
                request_comment,
                details
            ) VALUES (?, ?, 'pending', ?, ?, ?, ?)
            RETURNING id
        """
        )
        with self._connect() as conn:
            cursor = conn.execute(
                sql,
                (
                    workspace_id,
                    action,
                    requested_by,
                    target_user_id,
                    request_comment,
                    json.dumps(details or {}),
                ),
            )
            row = cursor.fetchone()
            conn.commit()
            if row:
                return int(row["id"])
        return None

    def get_approval_request(self, request_id: int) -> ApprovalRequest | None:
        """Get approval request by ID."""
        sql = self._prepare_sql(
            """
            SELECT * FROM approval_requests
            WHERE id = ?
            LIMIT 1
        """
        )
        with self._connect() as conn:
            cursor = conn.execute(sql, (request_id,))
            row = cursor.fetchone()
            if row:
                return _approval_from_row(row)
        return None

    def list_approval_requests(
        self,
        workspace_id: str,
        status: str | None = None,
        limit: int = 100,
    ) -> list[ApprovalRequest]:
        """List approval requests for a workspace ordered newest-first."""
        if status:
            sql = self._prepare_sql(
                """
                SELECT * FROM approval_requests
                WHERE workspace_id = ? AND status = ?
                ORDER BY requested_at DESC, id DESC
                LIMIT ?
            """
            )
            params: tuple[str | int, ...] = (workspace_id, status, limit)
        else:
            sql = self._prepare_sql(
                """
                SELECT * FROM approval_requests
                WHERE workspace_id = ?
                ORDER BY requested_at DESC, id DESC
                LIMIT ?
            """
            )
            params = (workspace_id, limit)

        with self._connect() as conn:
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()
            return [_approval_from_row(row) for row in rows]

    def decide_approval_request(
        self,
        request_id: int,
        decided_by: str,
        decision: str,
        decision_comment: str | None = None,
    ) -> ApprovalRequest | None:
        """Transition a pending approval request to approved or rejected."""
        decision_normalised = decision.strip().lower()
        if decision_normalised not in {"approved", "rejected"}:
            raise ValueError(f"Invalid decision: {decision}")

        current = self.get_approval_request(request_id)
        if current is None:
            return None
        if current.status != "pending":
            raise ValueError(
                f"Approval request {request_id} is already in state '{current.status}'"
            )

        sql = self._prepare_sql(
            """
            UPDATE approval_requests
            SET status = ?,
                decision_comment = ?,
                decided_by = ?,
                decided_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        )
        with self._connect() as conn:
            conn.execute(
                sql,
                (
                    decision_normalised,
                    decision_comment,
                    decided_by,
                    request_id,
                ),
            )
            conn.commit()
        return self.get_approval_request(request_id)


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
