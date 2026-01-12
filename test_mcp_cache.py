"""
Tests for MCP Result Caching.

Verifies cache functionality including TTL, invalidation, and multiple backends.
"""

import pickle
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from Tools.adapters.mcp_cache import (
    CacheBackend,
    CacheConfig,
    CacheEntry,
    CacheError,
    CacheStats,
    DiskCacheBackend,
    InvalidationStrategy,
    MCPCache,
    MemoryCacheBackend,
    cache_tool_call,
    create_cache,
    get_global_cache,
)


class TestCacheBackend:
    """Test CacheBackend enum."""

    def test_cache_backends(self):
        """Test that cache backends are defined correctly."""
        assert CacheBackend.MEMORY == "memory"
        assert CacheBackend.DISK == "disk"


class TestInvalidationStrategy:
    """Test InvalidationStrategy enum."""

    def test_invalidation_strategies(self):
        """Test that invalidation strategies are defined correctly."""
        assert InvalidationStrategy.TTL == "ttl"
        assert InvalidationStrategy.LRU == "lru"
        assert InvalidationStrategy.LFU == "lfu"
        assert InvalidationStrategy.MANUAL == "manual"


class TestCacheConfig:
    """Test CacheConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = CacheConfig()

        assert config.backend == CacheBackend.MEMORY
        assert config.strategy == InvalidationStrategy.TTL
        assert config.default_ttl_seconds == 300
        assert config.max_size == 1000
        assert config.enable_stats is True
        assert config.disk_cache_dir is None
        assert config.key_prefix == "mcp"

    def test_custom_config(self):
        """Test custom configuration values."""
        cache_dir = Path("/tmp/cache")
        config = CacheConfig(
            backend=CacheBackend.DISK,
            strategy=InvalidationStrategy.LRU,
            default_ttl_seconds=600,
            max_size=500,
            enable_stats=False,
            disk_cache_dir=cache_dir,
            key_prefix="test",
        )

        assert config.backend == CacheBackend.DISK
        assert config.strategy == InvalidationStrategy.LRU
        assert config.default_ttl_seconds == 600
        assert config.max_size == 500
        assert config.enable_stats is False
        assert config.disk_cache_dir == cache_dir
        assert config.key_prefix == "test"


class TestCacheEntry:
    """Test CacheEntry dataclass."""

    def test_entry_creation(self):
        """Test creating a cache entry."""
        entry = CacheEntry(
            key="test_key",
            value={"result": "data"},
        )

        assert entry.key == "test_key"
        assert entry.value == {"result": "data"}
        assert entry.access_count == 0
        assert entry.last_accessed is None
        assert entry.size_bytes == 0

    def test_entry_with_expiration(self):
        """Test cache entry with expiration."""
        expires_at = datetime.now() + timedelta(seconds=60)
        entry = CacheEntry(
            key="test_key",
            value="data",
            expires_at=expires_at,
        )

        assert not entry.is_expired()
        assert entry.expires_at == expires_at

    def test_expired_entry(self):
        """Test that expired entry is detected."""
        expires_at = datetime.now() - timedelta(seconds=1)
        entry = CacheEntry(
            key="test_key",
            value="data",
            expires_at=expires_at,
        )

        assert entry.is_expired()

    def test_entry_never_expires(self):
        """Test entry with no expiration."""
        entry = CacheEntry(
            key="test_key",
            value="data",
            expires_at=None,
        )

        assert not entry.is_expired()

    def test_touch_updates_metadata(self):
        """Test that touch updates access metadata."""
        entry = CacheEntry(key="test_key", value="data")

        assert entry.access_count == 0
        assert entry.last_accessed is None

        entry.touch()

        assert entry.access_count == 1
        assert entry.last_accessed is not None

        entry.touch()

        assert entry.access_count == 2


class TestCacheStats:
    """Test CacheStats dataclass."""

    def test_default_stats(self):
        """Test default statistics values."""
        stats = CacheStats()

        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.sets == 0
        assert stats.deletes == 0
        assert stats.evictions == 0
        assert stats.expirations == 0
        assert stats.errors == 0

    def test_hit_rate_calculation(self):
        """Test hit rate calculation."""
        stats = CacheStats()
        assert stats.hit_rate == 0.0

        stats.hits = 7
        stats.misses = 3
        assert stats.hit_rate == 0.7

        stats.hits = 10
        stats.misses = 0
        assert stats.hit_rate == 1.0

    def test_total_requests(self):
        """Test total requests calculation."""
        stats = CacheStats()
        assert stats.total_requests == 0

        stats.hits = 5
        stats.misses = 3
        assert stats.total_requests == 8

    def test_to_dict(self):
        """Test converting stats to dictionary."""
        stats = CacheStats(hits=10, misses=5, sets=15)
        stats_dict = stats.to_dict()

        assert stats_dict["hits"] == 10
        assert stats_dict["misses"] == 5
        assert stats_dict["sets"] == 15
        assert stats_dict["hit_rate"] == pytest.approx(0.667, abs=0.01)
        assert stats_dict["total_requests"] == 15


class TestMemoryCacheBackend:
    """Test MemoryCacheBackend implementation."""

    def test_backend_creation(self):
        """Test creating memory backend."""
        backend = MemoryCacheBackend()
        assert backend.size() == 0

    def test_set_and_get(self):
        """Test setting and getting entries."""
        backend = MemoryCacheBackend()
        entry = CacheEntry(key="key1", value="value1")

        backend.set("key1", entry)
        assert backend.size() == 1

        retrieved = backend.get("key1")
        assert retrieved is not None
        assert retrieved.value == "value1"

    def test_get_nonexistent(self):
        """Test getting non-existent entry."""
        backend = MemoryCacheBackend()
        assert backend.get("nonexistent") is None

    def test_delete(self):
        """Test deleting entries."""
        backend = MemoryCacheBackend()
        entry = CacheEntry(key="key1", value="value1")

        backend.set("key1", entry)
        assert backend.size() == 1

        deleted = backend.delete("key1")
        assert deleted is True
        assert backend.size() == 0

        deleted = backend.delete("key1")
        assert deleted is False

    def test_clear(self):
        """Test clearing all entries."""
        backend = MemoryCacheBackend()
        backend.set("key1", CacheEntry(key="key1", value="value1"))
        backend.set("key2", CacheEntry(key="key2", value="value2"))

        assert backend.size() == 2

        backend.clear()
        assert backend.size() == 0

    def test_keys(self):
        """Test getting all keys."""
        backend = MemoryCacheBackend()
        backend.set("key1", CacheEntry(key="key1", value="value1"))
        backend.set("key2", CacheEntry(key="key2", value="value2"))

        keys = backend.keys()
        assert set(keys) == {"key1", "key2"}

    def test_expired_entry_removed_on_get(self):
        """Test that expired entries are removed when accessed."""
        backend = MemoryCacheBackend()
        expires_at = datetime.now() - timedelta(seconds=1)
        entry = CacheEntry(key="key1", value="value1", expires_at=expires_at)

        backend.set("key1", entry)
        assert backend.size() == 1

        retrieved = backend.get("key1")
        assert retrieved is None
        assert backend.size() == 0


class TestDiskCacheBackend:
    """Test DiskCacheBackend implementation."""

    def test_backend_creation(self):
        """Test creating disk backend."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            backend = DiskCacheBackend(cache_dir)
            assert backend.cache_dir == cache_dir
            assert cache_dir.exists()

    def test_set_and_get(self):
        """Test setting and getting entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = DiskCacheBackend(Path(tmpdir))
            entry = CacheEntry(key="key1", value={"data": "value1"})

            backend.set("key1", entry)
            assert backend.size() == 1

            retrieved = backend.get("key1")
            assert retrieved is not None
            assert retrieved.value == {"data": "value1"}

    def test_get_nonexistent(self):
        """Test getting non-existent entry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = DiskCacheBackend(Path(tmpdir))
            assert backend.get("nonexistent") is None

    def test_delete(self):
        """Test deleting entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = DiskCacheBackend(Path(tmpdir))
            entry = CacheEntry(key="key1", value="value1")

            backend.set("key1", entry)
            assert backend.size() == 1

            deleted = backend.delete("key1")
            assert deleted is True
            assert backend.size() == 0

    def test_clear(self):
        """Test clearing all entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = DiskCacheBackend(Path(tmpdir))
            backend.set("key1", CacheEntry(key="key1", value="value1"))
            backend.set("key2", CacheEntry(key="key2", value="value2"))

            assert backend.size() == 2

            backend.clear()
            assert backend.size() == 0

    def test_persistence(self):
        """Test that entries persist across backend instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)

            # Create backend and set entry
            backend1 = DiskCacheBackend(cache_dir)
            backend1.set("key1", CacheEntry(key="key1", value="persistent_data"))

            # Create new backend instance
            backend2 = DiskCacheBackend(cache_dir)
            retrieved = backend2.get("key1")

            assert retrieved is not None
            assert retrieved.value == "persistent_data"

    def test_expired_entry_removed_on_get(self):
        """Test that expired entries are removed when accessed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = DiskCacheBackend(Path(tmpdir))
            expires_at = datetime.now() - timedelta(seconds=1)
            entry = CacheEntry(key="key1", value="value1", expires_at=expires_at)

            backend.set("key1", entry)
            assert backend.size() == 1

            retrieved = backend.get("key1")
            assert retrieved is None
            assert backend.size() == 0


class TestMCPCache:
    """Test MCPCache main class."""

    def test_cache_creation_memory(self):
        """Test creating cache with memory backend."""
        cache = MCPCache(CacheConfig(backend=CacheBackend.MEMORY))
        assert cache.config.backend == CacheBackend.MEMORY

    def test_cache_creation_disk(self):
        """Test creating cache with disk backend."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CacheConfig(
                backend=CacheBackend.DISK,
                disk_cache_dir=Path(tmpdir),
            )
            cache = MCPCache(config)
            assert cache.config.backend == CacheBackend.DISK

    def test_cache_creation_disk_without_dir_fails(self):
        """Test that disk backend requires cache directory."""
        config = CacheConfig(backend=CacheBackend.DISK)
        with pytest.raises(ValueError, match="disk_cache_dir required"):
            MCPCache(config)

    def test_generate_key(self):
        """Test cache key generation."""
        cache = MCPCache()

        key1 = cache.generate_key("tool1", {"arg": "value"})
        key2 = cache.generate_key("tool1", {"arg": "value"})
        key3 = cache.generate_key("tool1", {"arg": "different"})
        key4 = cache.generate_key("tool2", {"arg": "value"})

        # Same tool + args = same key
        assert key1 == key2

        # Different args = different key
        assert key1 != key3

        # Different tool = different key
        assert key1 != key4

        # Keys should contain tool name
        assert "tool1" in key1

    def test_generate_key_with_server(self):
        """Test cache key generation with server name."""
        cache = MCPCache()

        key1 = cache.generate_key("tool1", {"arg": "value"}, "server1")
        key2 = cache.generate_key("tool1", {"arg": "value"}, "server2")

        # Different server = different key
        assert key1 != key2

    def test_generate_key_argument_order_independent(self):
        """Test that argument order doesn't affect key."""
        cache = MCPCache()

        key1 = cache.generate_key("tool1", {"a": 1, "b": 2})
        key2 = cache.generate_key("tool1", {"b": 2, "a": 1})

        # Argument order shouldn't matter
        assert key1 == key2

    def test_set_and_get(self):
        """Test setting and getting cached results."""
        cache = MCPCache()

        result = {"status": "success", "data": [1, 2, 3]}
        cache.set("tool1", {"arg": "value"}, result)

        retrieved = cache.get("tool1", {"arg": "value"})
        assert retrieved == result

    def test_get_miss(self):
        """Test cache miss."""
        cache = MCPCache()

        result = cache.get("nonexistent", {"arg": "value"})
        assert result is None

    def test_delete(self):
        """Test deleting cached results."""
        cache = MCPCache()

        cache.set("tool1", {"arg": "value"}, "result")
        assert cache.get("tool1", {"arg": "value"}) is not None

        deleted = cache.delete("tool1", {"arg": "value"})
        assert deleted is True
        assert cache.get("tool1", {"arg": "value"}) is None

    def test_clear(self):
        """Test clearing entire cache."""
        cache = MCPCache()

        cache.set("tool1", {"arg": "value1"}, "result1")
        cache.set("tool2", {"arg": "value2"}, "result2")

        cache.clear()

        assert cache.get("tool1", {"arg": "value1"}) is None
        assert cache.get("tool2", {"arg": "value2"}) is None

    def test_ttl_expiration(self):
        """Test TTL-based expiration."""
        cache = MCPCache(CacheConfig(default_ttl_seconds=1))

        cache.set("tool1", {"arg": "value"}, "result")
        assert cache.get("tool1", {"arg": "value"}) == "result"

        # Wait for expiration
        time.sleep(1.1)

        assert cache.get("tool1", {"arg": "value"}) is None

    def test_custom_ttl(self):
        """Test custom TTL per entry."""
        cache = MCPCache(CacheConfig(default_ttl_seconds=10))

        # Set with custom short TTL
        cache.set("tool1", {"arg": "value"}, "result", ttl_seconds=1)
        assert cache.get("tool1", {"arg": "value"}) == "result"

        # Wait for expiration
        time.sleep(1.1)

        assert cache.get("tool1", {"arg": "value"}) is None

    def test_clear_expired(self):
        """Test clearing expired entries."""
        cache = MCPCache(CacheConfig(default_ttl_seconds=1))

        cache.set("tool1", {"arg": "value1"}, "result1")
        cache.set("tool2", {"arg": "value2"}, "result2", ttl_seconds=10)

        # Wait for first entry to expire
        time.sleep(1.1)

        removed = cache.clear_expired()
        assert removed == 1

        # Second entry should still exist
        assert cache.get("tool2", {"arg": "value2"}) == "result2"

    def test_stats_collection(self):
        """Test cache statistics collection."""
        cache = MCPCache(CacheConfig(enable_stats=True))

        stats = cache.get_stats()
        assert stats is not None
        assert stats.hits == 0
        assert stats.misses == 0

        # Cache miss
        cache.get("tool1", {"arg": "value"})
        assert stats.misses == 1

        # Cache set
        cache.set("tool1", {"arg": "value"}, "result")
        assert stats.sets == 1

        # Cache hit
        cache.get("tool1", {"arg": "value"})
        assert stats.hits == 1

        # Cache delete
        cache.delete("tool1", {"arg": "value"})
        assert stats.deletes == 1

    def test_stats_disabled(self):
        """Test that stats can be disabled."""
        cache = MCPCache(CacheConfig(enable_stats=False))

        stats = cache.get_stats()
        assert stats is None

    def test_max_size_eviction(self):
        """Test that cache respects max size."""
        cache = MCPCache(CacheConfig(max_size=3))

        # Fill cache to max
        cache.set("tool1", {"id": 1}, "result1")
        cache.set("tool1", {"id": 2}, "result2")
        cache.set("tool1", {"id": 3}, "result3")

        # All should be present
        assert cache.get("tool1", {"id": 1}) is not None
        assert cache.get("tool1", {"id": 2}) is not None
        assert cache.get("tool1", {"id": 3}) is not None

        # Add one more - should trigger eviction
        cache.set("tool1", {"id": 4}, "result4")

        # At least one entry should be evicted
        # (exact victim depends on strategy)
        stats = cache.get_stats()
        assert stats.evictions >= 1

    def test_lru_eviction(self):
        """Test LRU eviction strategy."""
        cache = MCPCache(
            CacheConfig(
                max_size=2,
                strategy=InvalidationStrategy.LRU,
            )
        )

        cache.set("tool1", {"id": 1}, "result1")
        time.sleep(0.1)
        cache.set("tool1", {"id": 2}, "result2")

        # Access first entry to make it recently used
        cache.get("tool1", {"id": 1})

        # Add third entry - should evict second (least recently used)
        cache.set("tool1", {"id": 3}, "result3")

        # First should still exist (recently accessed)
        assert cache.get("tool1", {"id": 1}) is not None
        # Third should exist (just added)
        assert cache.get("tool1", {"id": 3}) is not None

    def test_invalidate_by_tool(self):
        """Test invalidating all entries for a tool."""
        cache = MCPCache()

        cache.set("tool1", {"arg": "value1"}, "result1")
        cache.set("tool1", {"arg": "value2"}, "result2")
        cache.set("tool2", {"arg": "value3"}, "result3")

        # Invalidate tool1
        invalidated = cache.invalidate_by_tool("tool1")
        assert invalidated == 2

        # tool1 entries should be gone
        assert cache.get("tool1", {"arg": "value1"}) is None
        assert cache.get("tool1", {"arg": "value2"}) is None

        # tool2 entry should remain
        assert cache.get("tool2", {"arg": "value3"}) == "result3"


class TestCacheHelpers:
    """Test cache helper functions."""

    def test_create_cache(self):
        """Test create_cache helper."""
        cache = create_cache()
        assert isinstance(cache, MCPCache)

    def test_create_cache_with_config(self):
        """Test create_cache with custom config."""
        config = CacheConfig(default_ttl_seconds=600)
        cache = create_cache(config)
        assert cache.config.default_ttl_seconds == 600

    def test_get_global_cache(self):
        """Test global cache singleton."""
        cache1 = get_global_cache()
        cache2 = get_global_cache()

        # Should be same instance
        assert cache1 is cache2

    def test_cache_tool_call_miss(self):
        """Test cache_tool_call on cache miss."""
        cache = create_cache()
        call_count = 0

        def call_fn():
            nonlocal call_count
            call_count += 1
            return {"result": "data"}

        result = cache_tool_call(cache, "tool1", {"arg": "value"}, call_fn)

        assert result == {"result": "data"}
        assert call_count == 1

    def test_cache_tool_call_hit(self):
        """Test cache_tool_call on cache hit."""
        cache = create_cache()
        call_count = 0

        def call_fn():
            nonlocal call_count
            call_count += 1
            return {"result": "data"}

        # First call - should execute function
        result1 = cache_tool_call(cache, "tool1", {"arg": "value"}, call_fn)
        assert call_count == 1

        # Second call - should use cache
        result2 = cache_tool_call(cache, "tool1", {"arg": "value"}, call_fn)
        assert call_count == 1  # Not incremented
        assert result2 == result1

    def test_cache_tool_call_with_ttl(self):
        """Test cache_tool_call with custom TTL."""
        cache = create_cache()

        def call_fn():
            return {"result": "data"}

        result = cache_tool_call(
            cache, "tool1", {"arg": "value"}, call_fn, ttl_seconds=1
        )
        assert result == {"result": "data"}

        # Should be cached
        assert cache.get("tool1", {"arg": "value"}) is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
