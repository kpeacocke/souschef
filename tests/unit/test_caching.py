"""
Tests for caching system.

Tests cache backends, TTL expiration, size limits, and cache manager
functionality for various use cases.
"""

import time
from typing import Any

import pytest

from souschef.core.caching import (
    CacheEntry,
    CacheManager,
    FileHashCache,
    JSONSerializableCache,
    MemoryCache,
    get_cache_manager,
)


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_cache_entry_creation(self):
        """Test basic cache entry creation."""
        entry = CacheEntry(value="test_value")
        assert entry.value == "test_value"
        assert entry.access_count == 0
        assert entry.ttl_seconds is None

    def test_cache_entry_is_expired_no_ttl(self):
        """Test entry doesn't expire without TTL."""
        entry = CacheEntry(value="test", ttl_seconds=None)
        assert entry.is_expired() is False

    def test_cache_entry_is_expired_ttl_not_reached(self):
        """Test entry not expired when TTL not reached."""
        entry = CacheEntry(value="test", ttl_seconds=10)
        assert entry.is_expired() is False

    def test_cache_entry_is_expired_ttl_exceeded(self):
        """Test entry expired when TTL exceeded."""
        entry = CacheEntry(value="test", ttl_seconds=0.01)
        time.sleep(0.02)
        assert entry.is_expired() is True

    def test_cache_entry_touch(self):
        """Test touching updates access info."""
        entry = CacheEntry(value="test")
        initial_count = entry.access_count
        entry.touch()
        assert entry.access_count == initial_count + 1


class TestMemoryCache:
    """Tests for in-memory cache."""

    def test_memory_cache_get_set(self):
        """Test basic get and set operations."""
        cache: MemoryCache[str, str] = MemoryCache()
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_memory_cache_get_missing_key(self):
        """Test getting non-existent key returns None."""
        cache: MemoryCache[str, str] = MemoryCache()
        assert cache.get("missing") is None

    def test_memory_cache_delete(self):
        """Test deleting cache entry."""
        cache: MemoryCache[str, str] = MemoryCache()
        cache.set("key1", "value1")
        delete_result = cache.delete("key1")
        assert delete_result is True
        assert cache.get("key1") is None
        second_delete_result = cache.delete("key1")
        assert second_delete_result is False  # Already deleted

    def test_memory_cache_clear(self):
        """Test clearing all cache entries."""
        cache: MemoryCache[str, str] = MemoryCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert cache.size() == 0

    def test_memory_cache_ttl_expiration(self):
        """Test entries expire after TTL."""
        cache: MemoryCache[str, str] = MemoryCache()
        cache.set("key1", "value1", ttl_seconds=0.05)
        assert cache.get("key1") == "value1"
        time.sleep(0.1)
        assert cache.get("key1") is None

    def test_memory_cache_size_limit(self):
        """Test cache respects max size."""
        cache: MemoryCache[str, str] = MemoryCache(max_size=3)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        assert cache.size() == 3
        cache.set("key4", "value4")
        assert cache.size() == 3  # Evicted oldest

    def test_memory_cache_eviction(self):
        """Test LRU eviction of oldest accessed entry."""
        cache: MemoryCache[str, str] = MemoryCache(max_size=2)
        cache.set("key1", "value1")
        time.sleep(0.01)  # Ensure different timestamps
        cache.set("key2", "value2")
        # Access key1 to update its accessed_at
        cache.get("key1")
        time.sleep(0.01)
        # key2 is oldest, should be evicted
        cache.set("key3", "value3")
        assert cache.get("key1") is not None
        assert cache.get("key2") is None

    def test_memory_cache_stats(self):
        """Test cache statistics."""
        cache: MemoryCache[str, str] = MemoryCache(max_size=10)
        cache.set("key1", "value1")
        cache.get("key1")
        cache.get("key1")

        stats = cache.stats()
        assert stats["size"] == 1
        assert stats["max_size"] == 10
        assert stats["total_accesses"] == 2
        assert "utilisation_percent" in stats

    def test_memory_cache_default_ttl(self):
        """Test default TTL applied to entries."""
        cache: MemoryCache[str, str] = MemoryCache(default_ttl_seconds=0.05)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        time.sleep(0.1)
        assert cache.get("key1") is None


class TestFileHashCache:
    """Tests for file hash-based cache."""

    def test_file_hash_cache_get_set(self, tmp_path):
        """Test file hash cache with real file."""
        cache: FileHashCache[dict[str, Any]] = FileHashCache()
        test_file = tmp_path / "test.txt"
        test_file.write_text("content1")

        test_data = {"key": "value"}
        cache.set(str(test_file), test_data)
        assert cache.get(str(test_file)) == test_data

    def test_file_hash_cache_missing_file(self):
        """Test file hash cache with missing file."""
        cache: FileHashCache[dict[str, Any]] = FileHashCache()
        result = cache.get("/nonexistent/file.txt")
        assert result is None

    def test_file_hash_cache_invalidate_on_change(self, tmp_path):
        """Test cache invalidates when file changes."""
        cache: FileHashCache[dict[str, Any]] = FileHashCache()
        test_file = tmp_path / "test.txt"
        test_file.write_text("content1")

        test_data = {"key": "value"}
        cache.set(str(test_file), test_data)
        assert cache.get(str(test_file)) == test_data

        # Change file content
        test_file.write_text("content2")
        assert cache.get(str(test_file)) is None

    def test_file_hash_cache_delete(self, tmp_path):
        """Test deleting file cache entry."""
        cache: FileHashCache[dict[str, Any]] = FileHashCache()
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        test_data = {"key": "value"}
        cache.set(str(test_file), test_data)
        delete_result = cache.delete(str(test_file))
        assert delete_result is True
        assert cache.get(str(test_file)) is None

    def test_file_hash_cache_delete_after_file_change(self, tmp_path):
        """Test deleting cached entry after file content has changed."""
        cache: FileHashCache[dict[str, Any]] = FileHashCache()
        test_file = tmp_path / "test.txt"
        test_file.write_text("original content")

        # Cache the file with original content
        test_data = {"key": "original"}
        cache.set(str(test_file), test_data)

        # Change file content
        test_file.write_text("modified content")

        # Delete should still work using the stored hash
        delete_result = cache.delete(str(test_file))
        assert delete_result is True

        # Verify the old cache entry is gone
        assert cache.size() == 0
        assert str(test_file) not in cache._file_hashes

    def test_file_hash_cache_is_file_changed(self, tmp_path):
        """Test file change detection."""
        cache: FileHashCache[dict[str, Any]] = FileHashCache()
        test_file = tmp_path / "test.txt"
        test_file.write_text("content1")

        # Initially not cached
        assert cache.is_file_changed(str(test_file)) is True

        # Cache the file
        cache.set(str(test_file), {"data": "test"})

        # File unchanged
        assert cache.is_file_changed(str(test_file)) is False

        # Change file
        test_file.write_text("content2")
        assert cache.is_file_changed(str(test_file)) is True

    def test_file_hash_cache_cleans_up_old_entries(self, tmp_path):
        """Test that old cache entries are removed when file changes."""
        cache: FileHashCache[dict[str, Any]] = FileHashCache()
        test_file = tmp_path / "test.txt"

        # Cache original content
        test_file.write_text("content1")
        cache.set(str(test_file), {"version": 1})
        assert cache.size() == 1
        assert cache.get(str(test_file)) == {"version": 1}

        # Change file and cache again - old entry should be cleaned up
        test_file.write_text("content2")
        cache.set(str(test_file), {"version": 2})
        assert cache.size() == 1  # Still only 1 entry, old one was removed
        assert cache.get(str(test_file)) == {"version": 2}

        # Change file multiple times - verify no memory leak
        for i in range(3, 10):
            test_file.write_text(f"content{i}")
            cache.set(str(test_file), {"version": i})
            assert cache.size() == 1  # Always exactly 1 entry for this file
            assert cache.get(str(test_file)) == {"version": i}

        # Verify cleanup happens on get() as well
        test_file.write_text("final_content")
        result = cache.get(str(test_file))
        assert result is None  # Cache miss because content changed
        assert cache.size() == 0  # Old entry was cleaned up during get()


class TestJSONSerializableCache:
    """Tests for JSON serialisable cache."""

    def test_json_cache_get_set_json(self):
        """Test get and set JSON objects."""
        cache = JSONSerializableCache()
        obj = {"key": "value", "list": [1, 2, 3]}
        cache.set_json("test_key", obj)
        assert cache.get_json("test_key") == obj

    def test_json_cache_nested_structures(self):
        """Test caching complex nested structures."""
        cache = JSONSerializableCache()
        obj = {
            "nested": {
                "deep": {
                    "value": "test",
                    "list": [1, 2, {"inner": "value"}],
                }
            }
        }
        cache.set_json("complex", obj)
        assert cache.get_json("complex") == obj

    def test_json_cache_invalid_json(self):
        """Test invalid JSON objects are not cached."""
        cache = JSONSerializableCache()

        class NonSerializable:
            pass

        obj = NonSerializable()
        cache.set_json("invalid", obj)
        assert cache.get_json("invalid") is None

    def test_json_cache_corrupted_data(self):
        """Test handling of corrupted cached data."""
        cache = JSONSerializableCache()
        # Manually corrupt cache entry
        cache.set("bad_json", "{ invalid json }")
        assert cache.get_json("bad_json") is None


class TestCacheManager:
    """Tests for the cache manager."""

    def test_cache_manager_singleton(self):
        """Test cache manager returns same instance."""
        manager1 = get_cache_manager()
        manager2 = get_cache_manager()
        assert manager1 is manager2

    def test_cache_manager_inventory_cache(self, tmp_path):
        """Test inventory caching via manager."""
        manager = CacheManager()
        test_file = tmp_path / "inventory.ini"
        test_file.write_text(
            "[servers]\nhost1 ansible_host=10.0.0.1\n"
        )  # NOSONAR - test fixture

        inventory = {"hosts": {"host1": "10.0.0.1"}}  # NOSONAR - test fixture
        manager.cache_inventory(str(test_file), inventory)

        # Should return same inventory
        cached = manager.get_inventory(str(test_file))
        assert cached == inventory

        # Change file should invalidate
        test_file.write_text(
            "[servers]\nhost2 ansible_host=10.0.0.2\n"
        )  # NOSONAR - test fixture
        assert manager.get_inventory(str(test_file)) is None

    def test_cache_manager_assessment_cache(self):
        """Test assessment caching via manager."""
        manager = CacheManager()
        assessment = {
            "status": "success",
            "risks": ["risk1", "risk2"],
            "score": 85,
        }

        manager.cache_assessment("cookbook1", assessment)
        cached = manager.get_assessment("cookbook1")
        assert cached == assessment

    def test_cache_manager_galaxy_cache(self):
        """Test Galaxy API response caching."""
        manager = CacheManager()
        galaxy_data = {
            "name": "community.general",
            "version": "7.0.0",
            "download_count": 1000000,
        }

        manager.cache_galaxy_data("community.general", galaxy_data)
        cached = manager.get_galaxy_data("community.general")
        assert cached == galaxy_data

    def test_cache_manager_clear_all(self):
        """Test clearing all caches."""
        manager = CacheManager()
        manager.cache_inventory("test.ini", {"data": "test"})
        manager.cache_assessment("test", {"status": "ok"})
        manager.cache_galaxy_data("test", {"name": "test"})

        manager.clear_all()

        assert manager.get_inventory("test.ini") is None
        assert manager.get_assessment("test") is None
        assert manager.get_galaxy_data("test") is None

    def test_cache_manager_stats(self):
        """Test cache manager statistics."""
        manager = CacheManager()
        manager.inventory_cache.set("key1", {"data": "test"})
        manager.assessment_cache.set_json("key2", {"status": "ok"})

        stats = manager.stats()
        assert "inventory" in stats
        assert "file" in stats
        assert "assessment" in stats
        assert "galaxy" in stats
        assert stats["inventory"]["size"] == 1
        assert stats["assessment"]["size"] == 1


class TestCacheIntegration:
    """Integration tests for caching system."""

    def test_cache_consistency_multiple_operations(self):
        """Test cache remains consistent across multiple operations."""
        cache: MemoryCache[str, dict[str, Any]] = MemoryCache()

        # Set multiple values
        for i in range(10):
            cache.set(f"key{i}", {"id": i, "value": f"data{i}"})

        # Verify all values
        for i in range(10):
            assert cache.get(f"key{i}") == {"id": i, "value": f"data{i}"}

        # Delete some and verify others still exist
        cache.delete("key5")
        assert cache.get("key5") is None
        assert cache.get("key4") is not None

    def test_cache_with_different_ttls(self):
        """Test cache with mixed TTLs."""
        cache: MemoryCache[str, str] = MemoryCache(default_ttl_seconds=5)

        cache.set("short", "value1", ttl_seconds=0.05)
        cache.set("long", "value2", ttl_seconds=10)
        cache.set("default", "value3")  # Uses default TTL

        time.sleep(0.1)
        assert cache.get("short") is None
        assert cache.get("long") == "value2"
        assert cache.get("default") == "value3"

    def test_file_cache_with_multiple_files(self, tmp_path):
        """Test file cache with multiple files."""
        cache: FileHashCache[dict[str, Any]] = FileHashCache()

        # Create multiple files
        files = []
        for i in range(3):
            f = tmp_path / f"file{i}.txt"
            f.write_text(f"content{i}")
            files.append(f)

        # Cache data for each file
        for i, f in enumerate(files):
            cache.set(str(f), {"file_id": i, "data": f"data{i}"})

        # Verify all cached
        for i, f in enumerate(files):
            assert cache.get(str(f)) == {"file_id": i, "data": f"data{i}"}

    def test_cache_memory_efficiency(self):
        """Test cache memory usage patterns."""
        cache: MemoryCache[str, str] = MemoryCache(max_size=100)

        # Fill cache
        for i in range(100):
            cache.set(f"key{i}", f"value{i}" * 10)

        stats = cache.stats()
        assert stats["utilisation_percent"] == pytest.approx(100.0)

        # Add more entries, should maintain size
        for i in range(100, 150):
            cache.set(f"key{i}", f"value{i}" * 10)

        assert cache.size() == 100
