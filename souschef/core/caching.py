"""
Caching system for SousChef operations.

Provides in-memory caching with configurable expiration, size limits,
and support for various cache strategies.

Enables fast retrieval of parsed inventories, assessments, and API
responses while maintaining cache freshness.
"""

import hashlib
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Generic, TypeVar

K = TypeVar("K")
V = TypeVar("V")

# Cache configuration constants
DEFAULT_MAX_CACHE_SIZE = 1000  # Maximum cached items before eviction
DEFAULT_TTL_SECONDS = 300.0  # 5 minutes default cache lifetime
INVENTORY_CACHE_SIZE = 500  # Max inventory entries
INVENTORY_TTL_SECONDS = 300.0  # 5 minutes for inventory data
FILE_CACHE_TTL_SECONDS = 600.0  # 10 minutes for file-based cache
ASSESSMENT_CACHE_SIZE = 200  # Max assessment entries
ASSESSMENT_TTL_SECONDS = 900.0  # 15 minutes for assessments
GALAXY_CACHE_SIZE = 1000  # Max Galaxy API response entries
GALAXY_TTL_SECONDS = 3600.0  # 1 hour for Galaxy data (changes infrequently)


@dataclass
class CacheEntry(Generic[V]):
    """Single cache entry with metadata."""

    value: V
    created_at: float = field(default_factory=time.time)
    accessed_at: float = field(default_factory=time.time)
    ttl_seconds: float | None = None
    access_count: int = 0

    def is_expired(self) -> bool:
        """
        Check if cache entry has expired.

        Returns:
            True if entry has exceeded TTL, False otherwise.

        """
        if self.ttl_seconds is None:
            return False

        elapsed = time.time() - self.created_at
        return elapsed > self.ttl_seconds

    def touch(self) -> None:
        """Update access time and increment access counter."""
        self.accessed_at = time.time()
        self.access_count += 1


class CacheBackend(ABC, Generic[K, V]):
    """Abstract base class for cache backends."""

    @abstractmethod
    def get(self, key: K) -> V | None:
        """
        Retrieve value from cache.

        Args:
            key: Cache key.

        Returns:
            Cached value or None if not found or expired.

        """

    @abstractmethod
    def set(
        self,
        key: K,
        value: V,
        ttl_seconds: float | None = None,
    ) -> None:
        """
        Store value in cache.

        Args:
            key: Cache key.
            value: Value to cache.
            ttl_seconds: Time-to-live in seconds.

        """

    @abstractmethod
    def delete(self, key: K) -> bool:
        """
        Remove value from cache.

        Args:
            key: Cache key.

        Returns:
            True if entry was deleted, False if not found.

        """

    @abstractmethod
    def clear(self) -> None:
        """Remove all entries from cache."""

    @abstractmethod
    def size(self) -> int:
        """
        Get number of entries in cache.

        Returns:
            Number of cache entries.

        """


class MemoryCache(CacheBackend[K, V]):
    """
    In-memory cache with TTL and size limits.

    Stores entries in memory with optional expiration times.
    Automatically removes expired entries on access.
    """

    def __init__(
        self,
        max_size: int = DEFAULT_MAX_CACHE_SIZE,
        default_ttl_seconds: float | None = None,
    ):
        """
        Initialise memory cache.

        Args:
            max_size: Maximum number of entries (default: 1000).
            default_ttl_seconds: Default TTL for entries (optional).

        """
        self.max_size = max_size
        self.default_ttl_seconds = default_ttl_seconds
        self._cache: dict[K, CacheEntry[V]] = {}

    def get(self, key: K) -> V | None:
        """
        Retrieve value from cache.

        Args:
            key: Cache key.

        Returns:
            Cached value or None if not found or expired.

        """
        if key not in self._cache:
            return None

        entry = self._cache[key]

        if entry.is_expired():
            del self._cache[key]
            return None

        entry.touch()
        return entry.value

    def set(
        self,
        key: K,
        value: V,
        ttl_seconds: float | None = None,
    ) -> None:
        """
        Store value in cache.

        Args:
            key: Cache key.
            value: Value to cache.
            ttl_seconds: Time-to-live in seconds.

        """
        effective_ttl = ttl_seconds or self.default_ttl_seconds

        if len(self._cache) >= self.max_size:
            self._evict_oldest()

        entry = CacheEntry(value=value, ttl_seconds=effective_ttl)
        self._cache[key] = entry

    def delete(self, key: K) -> bool:
        """
        Remove value from cache.

        Args:
            key: Cache key.

        Returns:
            True if entry was deleted, False if not found.

        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> None:
        """Remove all entries from cache."""
        self._cache.clear()

    def size(self) -> int:
        """
        Get number of entries in cache.

        Returns:
            Number of cache entries.

        """
        return len(self._cache)

    def _evict_oldest(self) -> None:
        """Remove least recently accessed entry."""
        if not self._cache:
            return

        oldest_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].accessed_at,
        )
        del self._cache[oldest_key]

    def stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics.

        """
        total_accesses = sum(entry.access_count for entry in self._cache.values())
        non_expired = sum(1 for entry in self._cache.values() if not entry.is_expired())

        return {
            "size": self.size(),
            "max_size": self.max_size,
            "non_expired_entries": non_expired,
            "total_accesses": total_accesses,
            "utilisation_percent": (self.size() / self.max_size) * 100,
        }


class FileHashCache(CacheBackend[str, V]):
    """
    File content hash-based cache.

    Caches results keyed by file path and content hash.
    Automatically invalidates when file content changes.
    """

    def __init__(
        self,
        default_ttl_seconds: float | None = FILE_CACHE_TTL_SECONDS,
    ):
        """
        Initialise file hash cache.

        Args:
            default_ttl_seconds: Default TTL (default: 600 seconds / 10 min).

        """
        self.default_ttl_seconds = default_ttl_seconds
        self._cache: dict[str, CacheEntry[V]] = {}
        self._file_hashes: dict[str, str] = {}

    def _get_file_hash(self, file_path: str) -> str | None:
        """
        Compute hash of file content.

        Args:
            file_path: Path to file.

        Returns:
            Hash of file content or None if file not found.

        """
        try:
            path = Path(file_path)
            if not path.exists():
                return None

            with path.open("rb") as f:
                content = f.read()
                return hashlib.sha256(content).hexdigest()
        except OSError:
            return None

    def _make_key(self, file_path: str) -> str | None:
        """
        Create cache key from file path and hash.

        Args:
            file_path: Path to file.

        Returns:
            Cache key or None if file not found.

        """
        file_hash = self._get_file_hash(file_path)
        if file_hash is None:
            return None

        return f"{file_path}:{file_hash}"

    def get(self, key: str) -> V | None:
        """
        Retrieve cached value for file.

        Args:
            key: Path to file.

        Returns:
            Cached value or None if not found, expired, or file changed.

        """
        cache_key = self._make_key(key)
        if cache_key is None:
            return None

        if cache_key not in self._cache:
            return None

        entry = self._cache[cache_key]

        if entry.is_expired():
            del self._cache[cache_key]
            return None

        entry.touch()
        return entry.value

    def set(
        self,
        key: str,
        value: V,
        ttl_seconds: float | None = None,
    ) -> None:
        """
        Cache value for file.

        Args:
            key: Path to file.
            value: Value to cache.
            ttl_seconds: Time-to-live in seconds.

        """
        cache_key = self._make_key(key)
        if cache_key is None:
            return

        effective_ttl = ttl_seconds or self.default_ttl_seconds
        entry = CacheEntry(value=value, ttl_seconds=effective_ttl)
        self._cache[cache_key] = entry
        self._file_hashes[key] = cache_key.split(":")[-1]

    def delete(self, key: str) -> bool:
        """
        Remove cached value for file.

        Args:
            key: Path to file.

        Returns:
            True if entry was deleted, False if not found.

        """
        cache_key = self._make_key(key)
        if cache_key is None:
            return False

        if cache_key in self._cache:
            del self._cache[cache_key]
            self._file_hashes.pop(key, None)
            return True

        return False

    def clear(self) -> None:
        """Remove all entries from cache."""
        self._cache.clear()
        self._file_hashes.clear()

    def size(self) -> int:
        """
        Get number of entries in cache.

        Returns:
            Number of cache entries.

        """
        return len(self._cache)

    def is_file_changed(self, file_path: str) -> bool:
        """
        Check if file has changed since caching.

        Args:
            file_path: Path to file.

        Returns:
            True if file changed or not cached, False if unchanged.

        """
        if file_path not in self._file_hashes:
            return True

        current_hash = self._get_file_hash(file_path)
        if current_hash is None:
            return True

        return current_hash != self._file_hashes[file_path]


class JSONSerializableCache(MemoryCache[str, str]):
    """
    Cache for JSON-serialisable objects.

    Stores Python objects as JSON strings.
    """

    def get_json(self, key: str) -> Any | None:
        """
        Retrieve JSON-deserialised value.

        Args:
            key: Cache key.

        Returns:
            Deserialised Python object or None.

        """
        json_str = self.get(key)
        if json_str is None:
            return None

        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return None

    def set_json(
        self,
        key: str,
        obj: Any,
        ttl_seconds: float | None = None,
    ) -> None:
        """
        Store JSON-serialisable object.

        Args:
            key: Cache key.
            obj: Object to serialise and cache.
            ttl_seconds: Time-to-live in seconds.

        """
        try:
            json_str = json.dumps(obj)
            self.set(key, json_str, ttl_seconds)
        except (TypeError, ValueError):
            # Not JSON-serialisable; skip caching rather than raising.
            return


class CacheManager:
    """Manages multiple cache backends for different use cases."""

    def __init__(self):
        """Initialise cache manager with pre-configured backends."""
        self.inventory_cache: MemoryCache[str, dict[str, Any]] = MemoryCache(
            max_size=INVENTORY_CACHE_SIZE, default_ttl_seconds=INVENTORY_TTL_SECONDS
        )

        self.file_cache: FileHashCache[dict[str, Any]] = FileHashCache(
            default_ttl_seconds=FILE_CACHE_TTL_SECONDS
        )

        self.assessment_cache: JSONSerializableCache = JSONSerializableCache(
            max_size=ASSESSMENT_CACHE_SIZE, default_ttl_seconds=ASSESSMENT_TTL_SECONDS
        )

        self.galaxy_cache: JSONSerializableCache = JSONSerializableCache(
            max_size=GALAXY_CACHE_SIZE, default_ttl_seconds=GALAXY_TTL_SECONDS
        )

    def get_inventory(self, path: str) -> dict[str, Any] | None:
        """
        Get cached inventory.

        Args:
            path: Inventory file path.

        Returns:
            Cached inventory or None.

        """
        return self.file_cache.get(path)

    def cache_inventory(
        self,
        path: str,
        inventory: dict[str, Any],
    ) -> None:
        """
        Cache inventory result.

        Args:
            path: Inventory file path.
            inventory: Parsed inventory data.

        """
        self.file_cache.set(path, inventory)

    def get_assessment(self, key: str) -> Any | None:
        """
        Get cached assessment.

        Args:
            key: Assessment cache key.

        Returns:
            Cached assessment or None.

        """
        return self.assessment_cache.get_json(key)

    def cache_assessment(self, key: str, assessment: Any) -> None:
        """
        Cache assessment result.

        Args:
            key: Assessment cache key.
            assessment: Assessment data.

        """
        self.assessment_cache.set_json(key, assessment)

    def get_galaxy_data(self, key: str) -> Any | None:
        """
        Get cached Galaxy API response.

        Args:
            key: Galaxy data cache key.

        Returns:
            Cached data or None.

        """
        return self.galaxy_cache.get_json(key)

    def cache_galaxy_data(self, key: str, data: Any) -> None:
        """
        Cache Galaxy API response.

        Args:
            key: Galaxy data cache key.
            data: Galaxy API response data.

        """
        self.galaxy_cache.set_json(key, data)

    def clear_all(self) -> None:
        """Clear all caches."""
        self.inventory_cache.clear()
        self.file_cache.clear()
        self.assessment_cache.clear()
        self.galaxy_cache.clear()

    def stats(self) -> dict[str, Any]:
        """
        Get statistics for all caches.

        Returns:
            Dictionary with cache statistics.

        """
        return {
            "inventory": self.inventory_cache.stats(),
            "file": {"size": self.file_cache.size()},
            "assessment": {"size": self.assessment_cache.size()},
            "galaxy": {"size": self.galaxy_cache.size()},
        }


_cache_manager = CacheManager()


def get_cache_manager() -> CacheManager:
    """
    Get global cache manager instance.

    Returns:
        Global CacheManager instance.

    """
    return _cache_manager
