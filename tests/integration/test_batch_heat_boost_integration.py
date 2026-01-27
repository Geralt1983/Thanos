#!/usr/bin/env python3
"""
Integration Tests for Batch Heat Boosting in Memory Search.

Tests the complete flow of memory search with batch heat boosting:
- Memory search retrieves multiple results
- Heat values are updated in a single batch operation
- Access counts are incremented correctly
- Last accessed timestamps are updated
- Query efficiency is improved (1 query vs N queries)

Test Categories:
- TestBatchBoostIntegration: End-to-end search with batch boosting
- TestHeatUpdates: Verify heat, access_count, last_accessed updates
- TestQueryEfficiency: Verify database query count reduction
"""

import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, call
from typing import List, Dict, Any

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Tools.memory_v2.service import MemoryService
from Tools.memory_v2.heat import HeatService


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_database_connection():
    """Mock database connection and cursor for integration tests."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    # Setup cursor context manager
    mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
    mock_cursor.__exit__ = MagicMock(return_value=False)

    # Setup connection context manager
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)

    return mock_conn, mock_cursor


@pytest.fixture
def heat_service():
    """Create HeatService instance for testing."""
    with patch('Tools.memory_v2.heat.psycopg2.connect'):
        service = HeatService(database_url="postgresql://test")
        return service


@pytest.fixture
def memory_service():
    """Create MemoryService instance for testing."""
    with patch('Tools.memory_v2.service.psycopg2.connect'):
        with patch('Tools.memory_v2.service.EmbeddingService'):
            service = MemoryService(database_url="postgresql://test")
            return service


@pytest.fixture
def sample_search_results():
    """Sample search results before heat boosting."""
    return [
        {
            "id": "550e8400-e29b-41d4-a716-446655440001",
            "memory": "Orlando project kickoff meeting scheduled for next week",
            "content": "Orlando project kickoff meeting scheduled for next week",
            "metadata": {"client": "Orlando", "type": "observation"},
            "score": 0.15,
            "effective_score": 0.85
        },
        {
            "id": "550e8400-e29b-41d4-a716-446655440002",
            "memory": "Raleigh client requested API documentation updates",
            "content": "Raleigh client requested API documentation updates",
            "metadata": {"client": "Raleigh", "type": "task"},
            "score": 0.18,
            "effective_score": 0.82
        },
        {
            "id": "550e8400-e29b-41d4-a716-446655440003",
            "memory": "Memphis deployment went smoothly last Friday",
            "content": "Memphis deployment went smoothly last Friday",
            "metadata": {"client": "Memphis", "type": "observation"},
            "score": 0.22,
            "effective_score": 0.78
        },
        {
            "id": "550e8400-e29b-41d4-a716-446655440004",
            "memory": "Kentucky team needs training on new dashboard",
            "content": "Kentucky team needs training on new dashboard",
            "metadata": {"client": "Kentucky", "type": "task"},
            "score": 0.25,
            "effective_score": 0.75
        },
        {
            "id": "550e8400-e29b-41d4-a716-446655440005",
            "memory": "VersaCare integration shows promising results",
            "content": "VersaCare integration shows promising results",
            "metadata": {"client": "VersaCare", "type": "observation"},
            "score": 0.28,
            "effective_score": 0.72
        }
    ]


# =============================================================================
# Test Batch Boost Integration
# =============================================================================


class TestBatchBoostIntegration:
    """Integration tests for search with batch heat boosting."""

    def test_search_triggers_batch_boost(self, memory_service, sample_search_results):
        """Test that search operation triggers batch_boost_on_access()."""
        # Mock the vector search to return sample results
        with patch.object(memory_service, '_vector_search', return_value=sample_search_results):
            with patch.object(memory_service, '_apply_heat_ranking', return_value=sample_search_results):
                # Mock heat service batch_boost_on_access
                memory_service.heat_service.batch_boost_on_access = Mock(return_value=5)

                # Perform search
                results = memory_service.search("client projects", limit=5)

                # Verify batch_boost_on_access was called once
                memory_service.heat_service.batch_boost_on_access.assert_called_once()

                # Verify it was called with all 5 memory IDs
                call_args = memory_service.heat_service.batch_boost_on_access.call_args
                memory_ids = call_args[0][0]
                assert len(memory_ids) == 5
                assert "550e8400-e29b-41d4-a716-446655440001" in memory_ids
                assert "550e8400-e29b-41d4-a716-446655440005" in memory_ids

    def test_search_with_no_results(self, memory_service):
        """Test that search with no results doesn't call batch boost."""
        # Mock the vector search to return empty results
        with patch.object(memory_service, '_vector_search', return_value=[]):
            with patch.object(memory_service, '_apply_heat_ranking', return_value=[]):
                memory_service.heat_service.batch_boost_on_access = Mock()

                # Perform search
                results = memory_service.search("nonexistent query", limit=5)

                # Verify batch_boost_on_access was not called
                memory_service.heat_service.batch_boost_on_access.assert_not_called()

    def test_search_respects_limit(self, memory_service):
        """Test that batch boost only applies to limited results."""
        # Create 10 search results
        many_results = [
            {
                "id": f"550e8400-e29b-41d4-a716-44665544000{i}",
                "memory": f"Memory {i}",
                "content": f"Memory {i}",
                "score": 0.1 * i,
                "effective_score": 0.9 - (0.05 * i)
            }
            for i in range(10)
        ]

        with patch.object(memory_service, '_vector_search', return_value=many_results):
            with patch.object(memory_service, '_apply_heat_ranking', return_value=many_results):
                memory_service.heat_service.batch_boost_on_access = Mock(return_value=3)

                # Search with limit=3
                results = memory_service.search("query", limit=3)

                # Verify only 3 memories were boosted
                call_args = memory_service.heat_service.batch_boost_on_access.call_args
                memory_ids = call_args[0][0]
                assert len(memory_ids) == 3


# =============================================================================
# Test Heat Updates
# =============================================================================


class TestHeatUpdates:
    """Tests for heat value, access_count, and last_accessed updates."""

    def test_batch_boost_updates_heat_values(self, heat_service, mock_database_connection):
        """Test that batch boost updates heat values for all memories."""
        mock_conn, mock_cursor = mock_database_connection
        mock_cursor.rowcount = 3

        memory_ids = [
            "550e8400-e29b-41d4-a716-446655440001",
            "550e8400-e29b-41d4-a716-446655440002",
            "550e8400-e29b-41d4-a716-446655440003",
        ]

        with patch.object(heat_service, '_get_connection', return_value=mock_conn):
            result = heat_service.batch_boost_on_access(memory_ids)

        # Verify database UPDATE was executed
        assert mock_cursor.execute.call_count == 1

        # Verify query updates heat field
        query_call = mock_cursor.execute.call_args
        query = query_call[0][0]
        params = query_call[0][1]

        assert "UPDATE thanos_memories" in query
        assert "'heat'" in query
        assert "LEAST(%(max_heat)s" in query
        assert params["boost"] == 0.15  # Default access boost

    def test_batch_boost_updates_access_count(self, heat_service, mock_database_connection):
        """Test that batch boost increments access_count."""
        mock_conn, mock_cursor = mock_database_connection
        mock_cursor.rowcount = 2

        memory_ids = [
            "550e8400-e29b-41d4-a716-446655440001",
            "550e8400-e29b-41d4-a716-446655440002",
        ]

        with patch.object(heat_service, '_get_connection', return_value=mock_conn):
            heat_service.batch_boost_on_access(memory_ids)

        # Verify query increments access_count
        query_call = mock_cursor.execute.call_args
        query = query_call[0][0]

        assert "'access_count'" in query
        assert "COALESCE((payload->>'access_count')::int, 0) + 1" in query

    def test_batch_boost_updates_last_accessed(self, heat_service, mock_database_connection):
        """Test that batch boost updates last_accessed timestamp."""
        mock_conn, mock_cursor = mock_database_connection
        mock_cursor.rowcount = 2

        memory_ids = [
            "550e8400-e29b-41d4-a716-446655440001",
            "550e8400-e29b-41d4-a716-446655440002",
        ]

        with patch.object(heat_service, '_get_connection', return_value=mock_conn):
            heat_service.batch_boost_on_access(memory_ids)

        # Verify query updates last_accessed with NOW()
        query_call = mock_cursor.execute.call_args
        query = query_call[0][0]

        assert "'last_accessed'" in query
        assert "NOW()" in query

    def test_batch_boost_respects_max_heat_ceiling(self, heat_service, mock_database_connection):
        """Test that batch boost respects max_heat ceiling (2.0)."""
        mock_conn, mock_cursor = mock_database_connection
        mock_cursor.rowcount = 1

        memory_ids = ["550e8400-e29b-41d4-a716-446655440001"]

        with patch.object(heat_service, '_get_connection', return_value=mock_conn):
            heat_service.batch_boost_on_access(memory_ids)

        # Verify LEAST() enforces max_heat
        query_call = mock_cursor.execute.call_args
        query = query_call[0][0]
        params = query_call[0][1]

        assert "LEAST(%(max_heat)s" in query
        assert params["max_heat"] == 2.0


# =============================================================================
# Test Query Efficiency
# =============================================================================


class TestQueryEfficiency:
    """Tests for database query count reduction."""

    def test_single_query_for_multiple_memories(self, heat_service, mock_database_connection):
        """Test that boosting N memories uses only 1 database query."""
        mock_conn, mock_cursor = mock_database_connection
        mock_cursor.rowcount = 10

        # Boost 10 memories
        memory_ids = [f"550e8400-e29b-41d4-a716-44665544000{i}" for i in range(10)]

        with patch.object(heat_service, '_get_connection', return_value=mock_conn):
            heat_service.batch_boost_on_access(memory_ids)

        # Verify only 1 execute() call
        assert mock_cursor.execute.call_count == 1

        # Verify query uses batch UPDATE with ANY operator
        query_call = mock_cursor.execute.call_args
        query = query_call[0][0]
        params = query_call[0][1]

        assert "WHERE id = ANY(%(ids)s)" in query
        assert params["ids"] == memory_ids
        assert len(params["ids"]) == 10

    def test_batch_vs_individual_query_comparison(self, heat_service, mock_database_connection):
        """Compare batch operation vs individual operations."""
        mock_conn, mock_cursor = mock_database_connection

        memory_ids = [
            "550e8400-e29b-41d4-a716-446655440001",
            "550e8400-e29b-41d4-a716-446655440002",
            "550e8400-e29b-41d4-a716-446655440003",
            "550e8400-e29b-41d4-a716-446655440004",
            "550e8400-e29b-41d4-a716-446655440005",
        ]

        # Test batch operation
        mock_cursor.rowcount = 5
        with patch.object(heat_service, '_get_connection', return_value=mock_conn):
            heat_service.batch_boost_on_access(memory_ids)

        batch_query_count = mock_cursor.execute.call_count
        mock_cursor.reset_mock()

        # Simulate individual operations (what we used to do)
        mock_cursor.rowcount = 1
        with patch.object(heat_service, '_get_connection', return_value=mock_conn):
            for memory_id in memory_ids:
                heat_service.boost_on_access(memory_id)

        individual_query_count = mock_cursor.execute.call_count

        # Verify batch is more efficient
        assert batch_query_count == 1
        assert individual_query_count == 5
        assert batch_query_count < individual_query_count


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_batch_boost_with_duplicate_ids(self, heat_service, mock_database_connection):
        """Test batch boost with duplicate memory IDs (should handle gracefully)."""
        mock_conn, mock_cursor = mock_database_connection
        mock_cursor.rowcount = 2  # Only 2 unique IDs affected

        # List with duplicates
        memory_ids = [
            "550e8400-e29b-41d4-a716-446655440001",
            "550e8400-e29b-41d4-a716-446655440002",
            "550e8400-e29b-41d4-a716-446655440001",  # Duplicate
        ]

        with patch.object(heat_service, '_get_connection', return_value=mock_conn):
            result = heat_service.batch_boost_on_access(memory_ids)

        # Database will handle duplicates (only updates each row once)
        assert result == 2

    def test_batch_boost_with_nonexistent_ids(self, heat_service, mock_database_connection):
        """Test batch boost with nonexistent memory IDs."""
        mock_conn, mock_cursor = mock_database_connection
        mock_cursor.rowcount = 0  # No rows affected

        memory_ids = [
            "00000000-0000-0000-0000-000000000001",  # Doesn't exist
            "00000000-0000-0000-0000-000000000002",  # Doesn't exist
        ]

        with patch.object(heat_service, '_get_connection', return_value=mock_conn):
            result = heat_service.batch_boost_on_access(memory_ids)

        # Should return 0 (no rows updated)
        assert result == 0

    def test_search_with_mixed_valid_invalid_ids(self, memory_service, sample_search_results):
        """Test search handles results with missing or invalid IDs."""
        # Add a result without an ID
        results_with_invalid = sample_search_results.copy()
        results_with_invalid.append({
            "memory": "Memory without ID",
            "content": "Memory without ID",
            "score": 0.3
        })

        with patch.object(memory_service, '_vector_search', return_value=results_with_invalid):
            with patch.object(memory_service, '_apply_heat_ranking', return_value=results_with_invalid):
                memory_service.heat_service.batch_boost_on_access = Mock(return_value=5)

                # Perform search
                results = memory_service.search("query", limit=10)

                # Verify only valid IDs were passed to batch boost
                call_args = memory_service.heat_service.batch_boost_on_access.call_args
                memory_ids = call_args[0][0]
                assert len(memory_ids) == 5  # Only 5 valid IDs
                assert all(isinstance(id, str) for id in memory_ids)


# =============================================================================
# Test Performance Characteristics
# =============================================================================


class TestPerformanceCharacteristics:
    """Tests for performance and scalability characteristics."""

    def test_batch_boost_scales_linearly(self, heat_service, mock_database_connection):
        """Test that batch boost has O(1) query count regardless of input size."""
        mock_conn, mock_cursor = mock_database_connection

        # Test with different batch sizes
        for batch_size in [1, 5, 10, 50, 100]:
            mock_cursor.reset_mock()
            mock_cursor.rowcount = batch_size

            memory_ids = [f"550e8400-e29b-41d4-a716-44665544{i:04d}" for i in range(batch_size)]

            with patch.object(heat_service, '_get_connection', return_value=mock_conn):
                heat_service.batch_boost_on_access(memory_ids)

            # Always 1 query, regardless of batch size
            assert mock_cursor.execute.call_count == 1

    def test_batch_boost_transaction_atomicity(self, heat_service, mock_database_connection):
        """Test that batch boost operates in a single transaction."""
        mock_conn, mock_cursor = mock_database_connection
        mock_cursor.rowcount = 3

        memory_ids = [
            "550e8400-e29b-41d4-a716-446655440001",
            "550e8400-e29b-41d4-a716-446655440002",
            "550e8400-e29b-41d4-a716-446655440003",
        ]

        with patch.object(heat_service, '_get_connection', return_value=mock_conn):
            heat_service.batch_boost_on_access(memory_ids)

        # Verify transaction was committed
        mock_conn.commit.assert_called_once()

        # Verify rollback would be called on error
        mock_conn.reset_mock()
        mock_cursor.execute.side_effect = Exception("Database error")

        with patch.object(heat_service, '_get_connection', return_value=mock_conn):
            try:
                heat_service.batch_boost_on_access(memory_ids)
            except Exception:
                pass

        # Rollback should be called on error
        mock_conn.rollback.assert_called_once()
