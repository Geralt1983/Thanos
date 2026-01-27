"""
Unit tests for batch_boost_on_access() method in HeatService.

Tests the performance optimization that batches heat boosting operations
into a single database UPDATE query instead of N individual queries.

Tests cover:
1. Batch boosting multiple memory IDs
2. Empty list handling (graceful degradation)
3. Single memory ID (edge case)
4. Database query efficiency verification
5. Return value accuracy
"""

from unittest.mock import MagicMock, patch, call
import pytest
from Tools.memory_v2.heat import HeatService


@pytest.fixture
def mock_database_connection():
    """Mock database connection and cursor for HeatService tests."""
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
    """Create HeatService instance with mocked database."""
    with patch('Tools.memory_v2.heat.psycopg2.connect'):
        service = HeatService(database_url="postgresql://test")
        return service


class TestBatchBoostOnAccess:
    """Tests for batch_boost_on_access() method."""

    def test_batch_boost_multiple_memories(self, heat_service, mock_database_connection):
        """Test boosting multiple memory IDs in a single operation."""
        mock_conn, mock_cursor = mock_database_connection
        mock_cursor.rowcount = 5

        memory_ids = [
            "550e8400-e29b-41d4-a716-446655440001",
            "550e8400-e29b-41d4-a716-446655440002",
            "550e8400-e29b-41d4-a716-446655440003",
            "550e8400-e29b-41d4-a716-446655440004",
            "550e8400-e29b-41d4-a716-446655440005",
        ]

        with patch.object(heat_service, '_get_connection', return_value=mock_conn):
            result = heat_service.batch_boost_on_access(memory_ids)

        # Verify return value
        assert result == 5

        # Verify single database query was executed
        assert mock_cursor.execute.call_count == 1

        # Verify query contains batch UPDATE pattern
        query_call = mock_cursor.execute.call_args
        query = query_call[0][0]
        params = query_call[0][1]

        assert "UPDATE thanos_memories" in query
        assert "WHERE id = ANY(%(ids)s)" in query
        assert params["ids"] == memory_ids
        assert "max_heat" in params
        assert "boost" in params

    def test_batch_boost_empty_list(self, heat_service):
        """Test that empty list returns 0 without database query."""
        with patch.object(heat_service, '_get_connection') as mock_get_conn:
            result = heat_service.batch_boost_on_access([])

        # Should return 0 immediately without hitting database
        assert result == 0
        mock_get_conn.assert_not_called()

    def test_batch_boost_single_memory(self, heat_service, mock_database_connection):
        """Test boosting a single memory ID (edge case)."""
        mock_conn, mock_cursor = mock_database_connection
        mock_cursor.rowcount = 1

        memory_ids = ["550e8400-e29b-41d4-a716-446655440001"]

        with patch.object(heat_service, '_get_connection', return_value=mock_conn):
            result = heat_service.batch_boost_on_access(memory_ids)

        assert result == 1
        assert mock_cursor.execute.call_count == 1

    def test_batch_boost_updates_all_fields(self, heat_service, mock_database_connection):
        """Test that batch boost updates heat, last_accessed, and access_count."""
        mock_conn, mock_cursor = mock_database_connection
        mock_cursor.rowcount = 3

        memory_ids = [
            "550e8400-e29b-41d4-a716-446655440001",
            "550e8400-e29b-41d4-a716-446655440002",
            "550e8400-e29b-41d4-a716-446655440003",
        ]

        with patch.object(heat_service, '_get_connection', return_value=mock_conn):
            heat_service.batch_boost_on_access(memory_ids)

        query_call = mock_cursor.execute.call_args
        query = query_call[0][0]

        # Verify all required fields are updated
        assert "'heat'" in query
        assert "'last_accessed'" in query
        assert "'access_count'" in query
        assert "jsonb_build_object" in query

    def test_batch_boost_respects_max_heat(self, heat_service, mock_database_connection):
        """Test that batch boost respects max_heat ceiling."""
        mock_conn, mock_cursor = mock_database_connection
        mock_cursor.rowcount = 2

        memory_ids = [
            "550e8400-e29b-41d4-a716-446655440001",
            "550e8400-e29b-41d4-a716-446655440002",
        ]

        with patch.object(heat_service, '_get_connection', return_value=mock_conn):
            heat_service.batch_boost_on_access(memory_ids)

        query_call = mock_cursor.execute.call_args
        query = query_call[0][0]
        params = query_call[0][1]

        # Verify LEAST() function is used with max_heat
        assert "LEAST(%(max_heat)s" in query
        assert params["max_heat"] == heat_service.config["max_heat"]

    def test_batch_boost_transaction_rollback_on_error(self, heat_service):
        """Test that database errors trigger rollback."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Setup cursor to raise exception
        mock_cursor.execute.side_effect = Exception("Database error")
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(side_effect=Exception("Database error"))

        memory_ids = ["550e8400-e29b-41d4-a716-446655440001"]

        with patch.object(heat_service, '_get_connection', return_value=mock_conn):
            with pytest.raises(Exception):
                heat_service.batch_boost_on_access(memory_ids)

        # Verify rollback was called (via context manager)
        mock_conn.rollback.assert_called_once()

    def test_batch_boost_partial_success(self, heat_service, mock_database_connection):
        """Test behavior when some memory IDs don't exist."""
        mock_conn, mock_cursor = mock_database_connection
        # Only 3 of 5 memories were found and updated
        mock_cursor.rowcount = 3

        memory_ids = [
            "550e8400-e29b-41d4-a716-446655440001",
            "550e8400-e29b-41d4-a716-446655440002",
            "550e8400-e29b-41d4-a716-446655440003",
            "550e8400-e29b-41d4-a716-446655440004",  # Doesn't exist
            "550e8400-e29b-41d4-a716-446655440005",  # Doesn't exist
        ]

        with patch.object(heat_service, '_get_connection', return_value=mock_conn):
            result = heat_service.batch_boost_on_access(memory_ids)

        # Should return actual number of rows affected
        assert result == 3

    def test_batch_boost_increments_access_count(self, heat_service, mock_database_connection):
        """Test that access_count is incremented, not replaced."""
        mock_conn, mock_cursor = mock_database_connection
        mock_cursor.rowcount = 1

        memory_ids = ["550e8400-e29b-41d4-a716-446655440001"]

        with patch.object(heat_service, '_get_connection', return_value=mock_conn):
            heat_service.batch_boost_on_access(memory_ids)

        query_call = mock_cursor.execute.call_args
        query = query_call[0][0]

        # Verify access_count uses COALESCE and +1 pattern
        assert "COALESCE((payload->>'access_count')::int, 0) + 1" in query


class TestBatchBoostEfficiency:
    """Tests specifically focused on performance and query efficiency."""

    def test_batch_boost_single_query_for_ten_memories(self, heat_service, mock_database_connection):
        """Verify that 10 memories = 1 query (not 10 queries)."""
        mock_conn, mock_cursor = mock_database_connection
        mock_cursor.rowcount = 10

        # Simulate search results with 10 memories
        memory_ids = [f"550e8400-e29b-41d4-a716-44665544000{i}" for i in range(10)]

        with patch.object(heat_service, '_get_connection', return_value=mock_conn):
            result = heat_service.batch_boost_on_access(memory_ids)

        # Verify only ONE execute call
        assert mock_cursor.execute.call_count == 1
        assert result == 10

    def test_batch_boost_vs_individual_boost_query_count(self, heat_service, mock_database_connection):
        """Compare batch vs individual boost query counts."""
        mock_conn, mock_cursor = mock_database_connection

        memory_ids = [
            "550e8400-e29b-41d4-a716-446655440001",
            "550e8400-e29b-41d4-a716-446655440002",
            "550e8400-e29b-41d4-a716-446655440003",
        ]

        # Test batch method
        mock_cursor.rowcount = 3
        with patch.object(heat_service, '_get_connection', return_value=mock_conn):
            heat_service.batch_boost_on_access(memory_ids)

        batch_call_count = mock_cursor.execute.call_count

        # Reset mock
        mock_cursor.reset_mock()

        # Test individual boost_on_access calls
        mock_cursor.fetchone.return_value = (1.15,)
        with patch.object(heat_service, '_get_connection', return_value=mock_conn):
            for memory_id in memory_ids:
                heat_service.boost_on_access(memory_id)

        individual_call_count = mock_cursor.execute.call_count

        # Verify batch is more efficient
        assert batch_call_count == 1
        assert individual_call_count == 3
        assert individual_call_count > batch_call_count
