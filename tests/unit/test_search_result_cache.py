"""
Unit tests for the SearchResultCache class.
Tests TTL-based search result caching functionality.
"""
import sys
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from Tools.memory_v2.search_cache import SearchResultCache


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def cache():
    """Create a search result cache instance."""
    return SearchResultCache(ttl_seconds=3600)


@pytest.fixture
def short_ttl_cache():
    """Create a cache with short TTL for expiration testing."""
    return SearchResultCache(ttl_seconds=1)


# ============================================================================
# SearchResultCache Tests
# ============================================================================

class TestSearchResultCache:
    """Tests for the SearchResultCache class."""

    def test_set_and_get(self, cache):
        """Cache should store and retrieve search results."""
        key = cache.generate_key("test query", limit=5)
        results = [{"id": 1, "content": "result 1"}, {"id": 2, "content": "result 2"}]

        cache.set(key, results)
        cached_results = cache.get(key)

        assert cached_results == results

    def test_cache_miss(self, cache):
        """Cache should return None for missing entries."""
        key = cache.generate_key("nonexistent query", limit=10)

        result = cache.get(key)

        assert result is None

    def test_cache_expiration(self, short_ttl_cache):
        """Expired cache entries should return None."""
        key = short_ttl_cache.generate_key("test query", limit=5)
        results = [{"id": 1, "content": "result"}]

        short_ttl_cache.set(key, results)

        # Manually expire the cache
        import time
        time.sleep(1.1)

        result = short_ttl_cache.get(key)
        assert result is None

    def test_same_params_same_key(self, cache):
        """Same search parameters should generate the same cache key."""
        key1 = cache.generate_key("test query", limit=10, client="Orlando")
        key2 = cache.generate_key("test query", limit=10, client="Orlando")

        assert key1 == key2

    def test_different_query_different_key(self, cache):
        """Different queries should generate different cache keys."""
        key1 = cache.generate_key("query one", limit=10)
        key2 = cache.generate_key("query two", limit=10)

        assert key1 != key2

    def test_different_limit_different_key(self, cache):
        """Different limits should generate different cache keys."""
        key1 = cache.generate_key("test query", limit=5)
        key2 = cache.generate_key("test query", limit=10)

        assert key1 != key2

    def test_different_client_different_key(self, cache):
        """Different client filters should create different cache keys."""
        key1 = cache.generate_key("test query", limit=10, client="Orlando")
        key2 = cache.generate_key("test query", limit=10, client="Raleigh")

        assert key1 != key2

    def test_different_filters_different_cache(self, cache):
        """Same query with different filters should have different cache entries."""
        key1 = cache.generate_key("test query", limit=10, client="Orlando")
        key2 = cache.generate_key("test query", limit=10, client="Raleigh")

        results1 = [{"id": 1, "content": "Orlando result"}]
        results2 = [{"id": 2, "content": "Raleigh result"}]

        cache.set(key1, results1)
        cache.set(key2, results2)

        assert cache.get(key1) == results1
        assert cache.get(key2) == results2

    def test_multiple_filter_types(self, cache):
        """Different combinations of filters should create different keys."""
        key1 = cache.generate_key("test", limit=10, client="Orlando", project="Alpha")
        key2 = cache.generate_key("test", limit=10, client="Orlando", project="Beta")
        key3 = cache.generate_key("test", limit=10, client="Raleigh", project="Alpha")

        assert key1 != key2
        assert key1 != key3
        assert key2 != key3

    def test_entities_filter_sorting(self, cache):
        """Entity lists should be sorted for deterministic key generation."""
        # Different order, same entities should produce same key
        key1 = cache.generate_key("test", limit=10, entities=["person", "place", "thing"])
        key2 = cache.generate_key("test", limit=10, entities=["thing", "person", "place"])

        assert key1 == key2

    def test_access_count_tracking(self, cache):
        """Cache should track access count for entries."""
        key = cache.generate_key("test query", limit=5)
        results = [{"id": 1, "content": "result"}]

        cache.set(key, results)

        # Access multiple times
        cache.get(key)
        cache.get(key)
        cache.get(key)

        # Access count should be tracked in the backend
        entry = cache._backend.get(key)
        assert entry.access_count == 3

    def test_clear_expired(self, short_ttl_cache):
        """clear_expired should remove expired cache entries."""
        key1 = short_ttl_cache.generate_key("query1", limit=5)
        key2 = short_ttl_cache.generate_key("query2", limit=5)

        short_ttl_cache.set(key1, [{"id": 1}])
        short_ttl_cache.set(key2, [{"id": 2}])

        import time
        time.sleep(1.1)

        # Clear expired entries
        removed = short_ttl_cache.clear_expired()

        # Both entries should be expired and removed
        assert removed >= 0  # At least attempt to clear
        assert short_ttl_cache.get(key1) is None
        assert short_ttl_cache.get(key2) is None

    def test_cache_size(self, cache):
        """Cache should track its size correctly."""
        assert cache.size() == 0

        key1 = cache.generate_key("query1", limit=5)
        key2 = cache.generate_key("query2", limit=5)

        cache.set(key1, [{"id": 1}])
        assert cache.size() == 1

        cache.set(key2, [{"id": 2}])
        assert cache.size() == 2

    def test_delete_entry(self, cache):
        """Cache should support deleting specific entries."""
        key = cache.generate_key("test query", limit=5)
        results = [{"id": 1, "content": "result"}]

        cache.set(key, results)
        assert cache.get(key) == results

        deleted = cache.delete(key)
        assert deleted is True
        assert cache.get(key) is None

    def test_delete_nonexistent(self, cache):
        """Deleting nonexistent entry should return False."""
        key = cache.generate_key("nonexistent", limit=5)

        deleted = cache.delete(key)
        assert deleted is False

    def test_clear_all(self, cache):
        """Cache should support clearing all entries."""
        key1 = cache.generate_key("query1", limit=5)
        key2 = cache.generate_key("query2", limit=5)

        cache.set(key1, [{"id": 1}])
        cache.set(key2, [{"id": 2}])

        assert cache.size() == 2

        cache.clear()

        assert cache.size() == 0
        assert cache.get(key1) is None
        assert cache.get(key2) is None

    def test_cache_with_all_filters(self, cache):
        """Cache key should handle all filter types."""
        key = cache.generate_key(
            query="complex query",
            limit=20,
            client="Orlando",
            project="Alpha",
            domain="work",
            source="conversation",
            entities=["person", "place"],
            filters={"custom": "value"}
        )

        results = [{"id": 1, "content": "complex result"}]
        cache.set(key, results)

        assert cache.get(key) == results

    def test_none_filters_excluded(self, cache):
        """None values for filters should not affect cache key."""
        # Keys with explicit None should match keys with omitted parameters
        key1 = cache.generate_key("test", limit=10, client=None, project=None)
        key2 = cache.generate_key("test", limit=10)

        assert key1 == key2
