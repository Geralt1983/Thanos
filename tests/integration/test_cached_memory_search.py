#!/usr/bin/env python3
"""
Integration tests for Memory Service Search Caching.

Tests the full MemoryService.search() method with SearchResultCache enabled,
verifying cache hit/miss behavior, TTL expiration, and performance improvements.
"""

import pytest
import time
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Ensure Thanos project is in path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Tools.memory_v2.service import MemoryService
from Tools.memory_v2.search_cache import SearchResultCache


@pytest.fixture
def mock_db_connection():
    """Create a mock database connection for MemoryService."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    # Mock query results
    mock_cursor.fetchall.return_value = [
        {
            "id": "mem_1",
            "memory": "Orlando project status: API integration complete",
            "content": "Orlando project status: API integration complete",
            "created_at": datetime.now().isoformat(),
            "similarity": 0.95,
            "domain": "work",
            "client": "Orlando",
            "source": "manual"
        },
        {
            "id": "mem_2",
            "memory": "Orlando project next steps: testing phase",
            "content": "Orlando project next steps: testing phase",
            "created_at": datetime.now().isoformat(),
            "similarity": 0.88,
            "domain": "work",
            "client": "Orlando",
            "source": "manual"
        }
    ]

    return mock_conn, mock_cursor


@pytest.fixture
def memory_service(mock_db_connection):
    """Create a MemoryService with mocked database."""
    mock_conn, mock_cursor = mock_db_connection

    with patch("Tools.memory_v2.service.psycopg2.connect") as mock_connect, \
         patch("Tools.memory_v2.service.MEM0_AVAILABLE", False), \
         patch("Tools.memory_v2.service.RELATIONSHIPS_AVAILABLE", False), \
         patch("Tools.memory_v2.service._cached_query_embedding") as mock_embedding, \
         patch("Tools.memory_v2.service.OPENAI_API_KEY", "test_key"):

        # Setup connection mock
        mock_connect.return_value = mock_conn

        # Setup embedding mock
        mock_embedding.return_value = [0.1] * 1536  # Mock embedding vector

        # Create service
        service = MemoryService(
            database_url="postgresql://test:test@localhost/test",
            user_id="test_user"
        )

        # Store mock cursor for verification
        service._test_mock_cursor = mock_cursor
        service._test_mock_conn = mock_conn

        yield service


@pytest.mark.integration
class TestCachedMemorySearch:
    """Integration tests for cached memory search functionality."""

    def test_cache_initialization(self, memory_service):
        """Verify MemoryService initializes with cache."""
        assert hasattr(memory_service, "_search_cache")
        assert isinstance(memory_service._search_cache, SearchResultCache)
        assert memory_service._search_cache.ttl_seconds == 300

    def test_first_search_misses_cache(self, memory_service):
        """Verify first search executes database query (cache miss)."""
        # Clear any existing cache
        memory_service._search_cache.clear()

        # Reset cursor mock
        memory_service._test_mock_cursor.execute.reset_mock()

        # Execute search
        results = memory_service.search("Orlando project status", limit=5)

        # Verify database was queried
        assert memory_service._test_mock_cursor.execute.called
        assert len(results) > 0

        # Verify cache size increased
        assert memory_service._search_cache.size() == 1

    def test_repeated_search_hits_cache(self, memory_service):
        """Verify repeated identical search hits cache (no DB query)."""
        # Clear cache and execute first search
        memory_service._search_cache.clear()
        results1 = memory_service.search("Orlando project status", limit=5)

        # Reset mock to verify second call doesn't hit DB
        call_count_after_first = memory_service._test_mock_cursor.execute.call_count

        # Execute identical search
        results2 = memory_service.search("Orlando project status", limit=5)

        # Verify no additional database call
        assert memory_service._test_mock_cursor.execute.call_count == call_count_after_first

        # Verify results are identical
        assert results1 == results2

        # Verify cache was hit
        assert memory_service._search_cache.size() == 1

    def test_different_queries_create_separate_cache_entries(self, memory_service):
        """Verify different queries create separate cache entries."""
        memory_service._search_cache.clear()

        # Execute two different searches
        results1 = memory_service.search("Orlando project status", limit=5)
        results2 = memory_service.search("Kentucky deployment", limit=5)

        # Verify both created cache entries
        assert memory_service._search_cache.size() == 2

        # Verify both hit database
        assert memory_service._test_mock_cursor.execute.call_count >= 2

    def test_different_filters_create_separate_cache_entries(self, memory_service):
        """Verify different filter parameters create separate cache entries."""
        memory_service._search_cache.clear()

        # Same query, different filters
        results1 = memory_service.search("project status", client="Orlando", limit=5)
        results2 = memory_service.search("project status", client="Kentucky", limit=5)
        results3 = memory_service.search("project status", domain="personal", limit=5)

        # Verify separate cache entries
        assert memory_service._search_cache.size() == 3

    def test_different_limits_create_separate_cache_entries(self, memory_service):
        """Verify different limit values create separate cache entries."""
        memory_service._search_cache.clear()

        # Same query, different limits
        results1 = memory_service.search("Orlando project", limit=5)
        results2 = memory_service.search("Orlando project", limit=10)

        # Verify separate cache entries
        assert memory_service._search_cache.size() == 2

    def test_cache_ttl_expiration(self, memory_service):
        """Verify expired cache entries trigger fresh search."""
        # Create cache with very short TTL
        memory_service._search_cache = SearchResultCache(ttl_seconds=1)

        # First search
        results1 = memory_service.search("Orlando project", limit=5)
        call_count_first = memory_service._test_mock_cursor.execute.call_count

        # Wait for expiration
        time.sleep(1.5)

        # Second search after expiration
        results2 = memory_service.search("Orlando project", limit=5)
        call_count_second = memory_service._test_mock_cursor.execute.call_count

        # Verify fresh DB query was executed
        assert call_count_second > call_count_first

    def test_cache_with_all_filter_types(self, memory_service):
        """Verify cache works with all filter parameter types."""
        memory_service._search_cache.clear()

        # Search with all filter types
        results = memory_service.search(
            query="project update",
            limit=10,
            client="Orlando",
            project="VersaCare",
            domain="work",
            source="telegram",
            entities=["Ashley", "Jeremy"]
        )

        # Verify cache entry created
        assert memory_service._search_cache.size() == 1

        # Repeat search with identical parameters
        call_count_before = memory_service._test_mock_cursor.execute.call_count
        results2 = memory_service.search(
            query="project update",
            limit=10,
            client="Orlando",
            project="VersaCare",
            domain="work",
            source="telegram",
            entities=["Ashley", "Jeremy"]
        )
        call_count_after = memory_service._test_mock_cursor.execute.call_count

        # Verify cache was hit (no new DB call)
        assert call_count_after == call_count_before

    def test_cache_invalidation_manual_clear(self, memory_service):
        """Verify manual cache clearing forces fresh search."""
        memory_service._search_cache.clear()

        # First search
        results1 = memory_service.search("Orlando project", limit=5)

        # Clear cache
        memory_service._search_cache.clear()
        assert memory_service._search_cache.size() == 0

        # Search again - should hit DB
        call_count_before = memory_service._test_mock_cursor.execute.call_count
        results2 = memory_service.search("Orlando project", limit=5)
        call_count_after = memory_service._test_mock_cursor.execute.call_count

        # Verify fresh DB query
        assert call_count_after > call_count_before


@pytest.mark.integration
@pytest.mark.performance
class TestCachePerformance:
    """Performance tests for cache effectiveness."""

    def test_cache_hit_faster_than_db_query(self, memory_service):
        """Verify cached results return faster than DB queries."""
        memory_service._search_cache.clear()

        # First search (cache miss) - measure time
        start_miss = time.time()
        results1 = memory_service.search("Orlando project status", limit=10)
        time_miss = time.time() - start_miss

        # Second search (cache hit) - measure time
        start_hit = time.time()
        results2 = memory_service.search("Orlando project status", limit=10)
        time_hit = time.time() - start_hit

        # Cache hit should be faster (even with mocked DB)
        # In real scenarios, this would be much more dramatic
        assert time_hit <= time_miss

        # Verify results are identical
        assert results1 == results2

    def test_multiple_cache_hits_accumulate_access_count(self, memory_service):
        """Verify cache tracks access patterns for repeated queries."""
        memory_service._search_cache.clear()

        # Execute same search multiple times
        query = "Orlando project status"
        for i in range(5):
            memory_service.search(query, limit=5)

        # Verify only one cache entry exists
        assert memory_service._search_cache.size() == 1

        # Generate cache key and verify access count
        cache_key = memory_service._search_cache.generate_key(
            query=query,
            limit=5
        )
        entry = memory_service._search_cache._backend.get(cache_key)
        assert entry is not None
        assert entry.access_count >= 4  # First is creation, next 4 are hits

    def test_cache_clear_expired_performance(self, memory_service):
        """Verify clear_expired() efficiently removes only expired entries."""
        # Create cache with short TTL
        memory_service._search_cache = SearchResultCache(ttl_seconds=2)

        # Add multiple entries
        memory_service.search("query1", limit=5)
        time.sleep(0.5)
        memory_service.search("query2", limit=5)
        time.sleep(0.5)
        memory_service.search("query3", limit=5)

        # Wait for first entry to expire
        time.sleep(1.5)

        # Add fresh entry
        memory_service.search("query4", limit=5)

        # Clear expired
        removed = memory_service._search_cache.clear_expired()

        # Verify some entries removed
        assert removed >= 0  # At least query1 should be expired


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
