"""
IR versioning and compatibility management.

Handles version tracking, compatibility checking, and schema evolution
for the Intermediate Representation across different tool versions.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class IRVersion:
    """Represents an IR version with semantic versioning."""

    major: int
    minor: int
    patch: int = 0

    def __str__(self) -> str:
        """Return semantic version string."""
        return f"{self.major}.{self.minor}.{self.patch}"

    def to_tuple(self) -> tuple[int, int, int]:
        """Convert to tuple for comparison."""
        return (self.major, self.minor, self.patch)

    @staticmethod
    def parse(version_string: str) -> IRVersion:  # noqa: ARG004
        """
        Parse a semantic version string.

        Args:
            version_string: Version string like "1.0.0" or "2.1".

        Returns:
            IRVersion instance.

        Raises:
            ValueError: If version string is invalid.

        """
        try:
            parts = version_string.split(".")
            if len(parts) < 2:
                raise ValueError("Version must have at least major.minor")
            major = int(parts[0])
            minor = int(parts[1])
            patch = int(parts[2]) if len(parts) > 2 else 0
            return IRVersion(major=major, minor=minor, patch=patch)
        except (ValueError, IndexError) as e:
            raise ValueError(f"Invalid version format: {version_string}") from e

    def is_compatible_with(self, other: IRVersion) -> bool:
        """
        Check if this version is compatible with another.

        Version A is compatible with B if:
        - Major versions are equal (major versions indicate breaking changes)
        - Minor and patch can differ (backward compatible)

        Args:
            other: Version to check compatibility with.

        Returns:
            True if versions are compatible.

        """
        return self.major == other.major

    def __lt__(self, other: IRVersion) -> bool:
        """Check if this version is less than another."""
        return self.to_tuple() < other.to_tuple()

    def __le__(self, other: IRVersion) -> bool:
        """Check if this version is less than or equal to another."""
        return self.to_tuple() <= other.to_tuple()

    def __gt__(self, other: IRVersion) -> bool:
        """Check if this version is greater than another."""
        return self.to_tuple() > other.to_tuple()

    def __ge__(self, other: IRVersion) -> bool:
        """Check if this version is greater than or equal to another."""
        return self.to_tuple() >= other.to_tuple()

    def __eq__(self, other: object) -> bool:
        """Check if versions are equal."""
        if not isinstance(other, IRVersion):
            return NotImplemented
        return self.to_tuple() == other.to_tuple()


@dataclass
class SchemaMigration:
    """Defines a migration path between two IR schema versions."""

    from_version: IRVersion
    to_version: IRVersion
    transformation: Callable[[dict[str, Any]], dict[str, Any]]
    description: str = ""

    def migrate(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Apply this migration to IR data.

        Args:
            data: IR data in the older version format.

        Returns:
            IR data transformed to the newer version format.

        """
        return self.transformation(data)


class IRVersionManager:
    """Manages IR versioning, compatibility checking, and schema evolution."""

    def __init__(self) -> None:
        """Initialise version manager."""
        self.current_version = IRVersion(major=1, minor=0, patch=0)
        self.supported_versions: list[IRVersion] = [
            IRVersion(major=1, minor=0, patch=0),
        ]
        self.migrations: list[SchemaMigration] = []

    def register_migration(self, migration: SchemaMigration) -> None:
        """
        Register a schema migration.

        Args:
            migration: Migration to register.

        """
        self.migrations.append(migration)

    def get_migrations_path(
        self, from_version: IRVersion, to_version: IRVersion
    ) -> list[SchemaMigration]:
        """
        Find a migration path between two versions.

        Args:
            from_version: Starting version.
            to_version: Target version.

        Returns:
            List of migrations to apply in order.

        Raises:
            ValueError: If no migration path exists.

        """
        if from_version == to_version:
            return []

        # For now, support only single-step migrations
        for migration in self.migrations:
            if (
                migration.from_version == from_version
                and migration.to_version == to_version
            ):
                return [migration]

        raise ValueError(f"No migration path from {from_version} to {to_version}")

    def migrate_data(
        self,
        data: dict[str, Any],
        from_version: IRVersion,
        to_version: IRVersion,
    ) -> dict[str, Any]:
        """
        Migrate IR data from one version to another.

        Args:
            data: IR data to migrate.
            from_version: Current version of the data.
            to_version: Target version.

        Returns:
            Migrated data in the target version format.

        Raises:
            ValueError: If migration is not possible.

        """
        migrations = self.get_migrations_path(from_version, to_version)
        result = data
        for migration in migrations:
            result = migration.migrate(result)
        return result

    def is_version_compatible(self, version: IRVersion) -> bool:
        """
        Check if a version is supported.

        Args:
            version: Version to check.

        Returns:
            True if version is compatible with current version.

        """
        # Version is compatible if major version matches current
        return version.major == self.current_version.major or (
            version in self.supported_versions
        )

    def add_supported_version(self, version: IRVersion) -> None:
        """
        Register a supported version.

        Args:
            version: Version to mark as supported.

        """
        if version not in self.supported_versions:
            self.supported_versions.append(version)
            self.supported_versions.sort(key=lambda v: v.to_tuple(), reverse=True)

    def get_version_info(self) -> dict[str, Any]:
        """
        Get information about current version and supported versions.

        Returns:
            Dictionary with version information.

        """
        return {
            "current_version": str(self.current_version),
            "supported_versions": [str(v) for v in self.supported_versions],
            "migrations_available": len(self.migrations),
        }


# Global version manager instance
_version_manager: IRVersionManager | None = None


def get_version_manager() -> IRVersionManager:
    """
    Get or create the global version manager.

    Returns:
        Global IRVersionManager instance.

    """
    global _version_manager
    if _version_manager is None:
        _version_manager = IRVersionManager()
    return _version_manager
