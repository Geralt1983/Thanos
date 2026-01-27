#!/usr/bin/env python3
"""
Unit tests for StateStore connection pooling behavior.

Tests cover:
- Connection reuse across multiple operations
- PRAGMA execution and configuration
- Proper cleanup via close() and __del__()
- Isolation between multiple StateStore instances
- High-frequency methods using pooled connections
- Performance characteristics of connection pooling
"""

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, call

import pytest

from Tools.state_store.store import StateStore


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_db_path(tmp_path):
    """Create a temporary database path."""
    return tmp_path / "test_pool.db"


@pytest.fixture
def store(temp_db_path):
    """Create a StateStore instance with a temporary database."""
    return StateStore(db_path=temp_db_path)


# ============================================================================
# Connection Pooling Tests
# ============================================================================


class TestConnectionPooling:
    """Tests for connection pooling behavior."""

    def test_pooled_connection_initialized_as_none(self, temp_db_path):
        """Test that _conn is initialized to None (lazy initialization)."""
        store = StateStore(db_path=temp_db_path)
        assert store._conn is None

    def test_pooled_connection_created_on_first_access(self, store):
        """Test that pooled connection is created on first access."""
        assert store._conn is None
        conn = store._get_pooled_connection()
        assert store._conn is not None
        assert isinstance(conn, sqlite3.Connection)

    def test_same_connection_returned_on_multiple_calls(self, store):
        """Test that the same connection object is returned on multiple calls."""
        conn1 = store._get_pooled_connection()
        conn2 = store._get_pooled_connection()
        conn3 = store._get_pooled_connection()

        # All should be the same object
        assert conn1 is conn2
        assert conn2 is conn3
        assert id(conn1) == id(conn2) == id(conn3)

    def test_connection_properly_configured(self, store):
        """Test that pooled connection has proper PRAGMA settings."""
        conn = store._get_pooled_connection()

        # Check foreign keys are enabled
        cursor = conn.execute("PRAGMA foreign_keys")
        foreign_keys_enabled = cursor.fetchone()[0]
        assert foreign_keys_enabled == 1

        # Check WAL mode is enabled
        cursor = conn.execute("PRAGMA journal_mode")
        journal_mode = cursor.fetchone()[0]
        assert journal_mode == "wal"

    def test_connection_row_factory_configured(self, store):
        """Test that pooled connection has Row factory configured."""
        conn = store._get_pooled_connection()
        assert conn.row_factory == sqlite3.Row

    def test_pragma_only_executed_once(self, temp_db_path):
        """Test that PRAGMA statements are only executed on first connection creation."""
        with patch('sqlite3.Connection.execute') as mock_execute:
            # Create a real connection for the mock to wrap
            real_conn = sqlite3.connect(str(temp_db_path))
            mock_execute.return_value = Mock()

            # Set up the mock to return the real connection
            with patch('sqlite3.connect', return_value=real_conn):
                store = StateStore(db_path=temp_db_path)

                # Reset mock to ignore init calls
                mock_execute.reset_mock()

                # Call _get_pooled_connection multiple times
                store._get_pooled_connection()
                store._get_pooled_connection()
                store._get_pooled_connection()

                # PRAGMA should only be called twice (foreign_keys and journal_mode) on first access
                pragma_calls = [
                    c for c in mock_execute.call_args_list
                    if c[0][0].startswith("PRAGMA")
                ]
                # Should be exactly 2 PRAGMA calls from the first access only
                assert len(pragma_calls) == 2

            real_conn.close()


# ============================================================================
# Connection Cleanup Tests
# ============================================================================


class TestConnectionCleanup:
    """Tests for connection cleanup and resource management."""

    def test_close_method_closes_connection(self, store):
        """Test that close() closes the pooled connection."""
        # Create connection
        conn = store._get_pooled_connection()
        assert store._conn is not None

        # Close it
        store.close()

        # Connection should be None
        assert store._conn is None

        # Original connection should be closed
        with pytest.raises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")

    def test_close_method_sets_conn_to_none(self, store):
        """Test that close() sets _conn to None."""
        store._get_pooled_connection()
        assert store._conn is not None

        store.close()
        assert store._conn is None

    def test_close_method_idempotent(self, store):
        """Test that calling close() multiple times doesn't cause errors."""
        store._get_pooled_connection()
        store.close()
        store.close()  # Should not raise error
        store.close()  # Should not raise error
        assert store._conn is None

    def test_close_without_connection_doesnt_error(self, store):
        """Test that close() works even if no connection was created."""
        # Don't create a connection
        assert store._conn is None

        # close() should not raise error
        store.close()
        assert store._conn is None

    def test_close_handles_exceptions_silently(self, store):
        """Test that close() handles exceptions during close silently."""
        # Create connection
        store._get_pooled_connection()

        # Mock the connection's close to raise an exception
        with patch.object(store._conn, 'close', side_effect=Exception("Close error")):
            # Should not raise exception
            store.close()

        # _conn should still be set to None
        assert store._conn is None

    def test_destructor_calls_close(self, temp_db_path):
        """Test that __del__() calls close()."""
        store = StateStore(db_path=temp_db_path)
        store._get_pooled_connection()

        with patch.object(store, 'close') as mock_close:
            # Trigger destructor
            store.__del__()
            mock_close.assert_called_once()

    def test_connection_can_be_recreated_after_close(self, store):
        """Test that connection can be created again after closing."""
        # Create and close connection
        conn1 = store._get_pooled_connection()
        store.close()

        # Create new connection
        conn2 = store._get_pooled_connection()

        # Should be a different object
        assert conn1 is not conn2
        assert store._conn is conn2


# ============================================================================
# Multiple Instance Tests
# ============================================================================


class TestMultipleInstances:
    """Tests for connection isolation between multiple StateStore instances."""

    def test_separate_instances_have_separate_connections(self, tmp_path):
        """Test that multiple StateStore instances have separate connections."""
        db_path1 = tmp_path / "test1.db"
        db_path2 = tmp_path / "test2.db"

        store1 = StateStore(db_path=db_path1)
        store2 = StateStore(db_path=db_path2)

        conn1 = store1._get_pooled_connection()
        conn2 = store2._get_pooled_connection()

        # Should be different connection objects
        assert conn1 is not conn2
        assert id(conn1) != id(conn2)

        # Clean up
        store1.close()
        store2.close()

    def test_same_db_different_instances_have_separate_connections(self, temp_db_path):
        """Test that multiple instances pointing to same DB have separate connections."""
        store1 = StateStore(db_path=temp_db_path)
        store2 = StateStore(db_path=temp_db_path)

        conn1 = store1._get_pooled_connection()
        conn2 = store2._get_pooled_connection()

        # Should be different connection objects (different instances)
        assert conn1 is not conn2

        # But should point to same database
        assert store1.db_path == store2.db_path

        # Clean up
        store1.close()
        store2.close()

    def test_closing_one_instance_doesnt_affect_other(self, temp_db_path):
        """Test that closing one instance doesn't affect another instance."""
        store1 = StateStore(db_path=temp_db_path)
        store2 = StateStore(db_path=temp_db_path)

        conn1 = store1._get_pooled_connection()
        conn2 = store2._get_pooled_connection()

        # Close store1
        store1.close()

        # store2 should still work
        assert store2._conn is not None
        cursor = conn2.execute("SELECT 1")
        assert cursor.fetchone()[0] == 1

        # Clean up
        store2.close()


# ============================================================================
# High-Frequency Method Tests
# ============================================================================


class TestHighFrequencyMethods:
    """Tests for high-frequency methods using pooled connections."""

    def test_count_tasks_uses_pooled_connection(self, store):
        """Test that count_tasks() uses the pooled connection."""
        # Create some tasks
        store.create_task(title="Task 1", domain="work")
        store.create_task(title="Task 2", domain="work")

        # Call count_tasks - should use pooled connection
        count = store.count_tasks()
        assert count == 2

        # Verify pooled connection exists and was reused
        assert store._conn is not None

    def test_count_commitments_uses_pooled_connection(self, store):
        """Test that count_commitments() uses the pooled connection."""
        # Create a commitment
        store.create_commitment(
            title="Commitment 1",
            stakeholder="John",
            deadline=None,
            domain="work"
        )

        # Call count_commitments
        count = store.count_commitments()
        assert count == 1
        assert store._conn is not None

    def test_count_brain_dumps_uses_pooled_connection(self, store):
        """Test that count_brain_dumps() uses the pooled connection."""
        # Create a brain dump
        store.create_brain_dump(content="Test thought", context="work")

        # Call count_brain_dumps
        count = store.count_brain_dumps()
        assert count == 1
        assert store._conn is not None

    def test_get_active_focus_uses_pooled_connection(self, store):
        """Test that get_active_focus() uses the pooled connection."""
        # Set a focus
        store.set_focus("Test Focus")

        # Get active focus
        focus = store.get_active_focus()
        assert len(focus) > 0
        assert store._conn is not None

    def test_export_summary_reuses_connection(self, store):
        """Test that export_summary() benefits from connection reuse."""
        # Create diverse data
        store.create_task(title="Task 1", domain="work")
        store.create_commitment(
            title="Commitment 1",
            stakeholder="John",
            deadline=None,
            domain="work"
        )
        store.create_brain_dump(content="Thought", context="work")

        # Call export_summary - it calls multiple count methods
        summary = store.export_summary()

        # Verify summary structure
        assert "tasks" in summary
        assert "commitments" in summary
        assert "brain_dumps" in summary
        assert "focus_areas" in summary

        # Verify pooled connection was created and used
        assert store._conn is not None

        # Verify data is correct
        assert summary["tasks"]["total"] == 1
        assert summary["commitments"]["total"] == 1
        assert summary["brain_dumps"]["total"] == 1


# ============================================================================
# Connection State Tests
# ============================================================================


class TestConnectionState:
    """Tests for connection state management."""

    def test_connection_survives_commit(self, store):
        """Test that pooled connection survives explicit commits."""
        conn = store._get_pooled_connection()
        conn.execute("BEGIN")
        conn.commit()

        # Connection should still be the same
        conn2 = store._get_pooled_connection()
        assert conn is conn2

    def test_connection_survives_rollback(self, store):
        """Test that pooled connection survives rollbacks."""
        conn = store._get_pooled_connection()
        conn.execute("BEGIN")
        conn.rollback()

        # Connection should still be the same
        conn2 = store._get_pooled_connection()
        assert conn is conn2

    def test_operations_share_transaction_context(self, store):
        """Test that multiple operations on pooled connection share transaction context."""
        # Create a task
        task_id = store.create_task(title="Test Task", domain="work")

        # Get the connection
        conn = store._get_pooled_connection()

        # Manually query the task (should see it even without explicit commit)
        cursor = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        result = cursor.fetchone()
        assert result is not None
        assert result["title"] == "Test Task"


# ============================================================================
# Performance Characteristics Tests
# ============================================================================


class TestPerformanceCharacteristics:
    """Tests for performance characteristics of connection pooling."""

    def test_no_connection_leaks_after_many_operations(self, store):
        """Test that repeated operations don't leak connections."""
        # Perform many operations
        for i in range(100):
            store.count_tasks()
            store.count_commitments()
            store.count_brain_dumps()

        # Should still have only one connection
        conn1 = store._get_pooled_connection()
        conn2 = store._get_pooled_connection()
        assert conn1 is conn2

    def test_connection_remains_functional_after_many_queries(self, store):
        """Test that pooled connection remains functional after many queries."""
        # Create some test data
        for i in range(10):
            store.create_task(title=f"Task {i}", domain="work")

        # Perform many queries
        for _ in range(50):
            count = store.count_tasks()
            assert count == 10

        # Connection should still work
        conn = store._get_pooled_connection()
        cursor = conn.execute("SELECT COUNT(*) FROM tasks")
        assert cursor.fetchone()[0] == 10


# ============================================================================
# Integration Tests
# ============================================================================


class TestConnectionPoolingIntegration:
    """Integration tests for connection pooling with actual operations."""

    def test_create_and_query_with_pooled_connection(self, store):
        """Test creating and querying data with pooled connection."""
        # Create task
        task_id = store.create_task(title="Test Task", domain="work")

        # Query using count (which uses pooled connection)
        count = store.count_tasks()
        assert count == 1

        # Verify same connection was used
        conn = store._get_pooled_connection()
        cursor = conn.execute("SELECT COUNT(*) FROM tasks")
        assert cursor.fetchone()[0] == 1

    def test_mixed_pooled_and_context_manager_connections(self, store):
        """Test that pooled and context manager connections can coexist."""
        # Use context manager to create task
        task_id = store.create_task(title="Test Task", domain="work")

        # Use pooled connection to query
        count = store.count_tasks()
        assert count == 1

        # Both should see the same data
        tasks = store.get_tasks()
        assert len(tasks) == 1
        assert tasks[0].id == task_id

    def test_pooled_connection_sees_context_manager_changes(self, store):
        """Test that pooled connection sees changes made by context manager."""
        # Create task using create_task (which uses context manager)
        store.create_task(title="Task 1", domain="work")

        # Verify using pooled connection
        conn = store._get_pooled_connection()
        cursor = conn.execute("SELECT COUNT(*) FROM tasks")
        assert cursor.fetchone()[0] == 1

        # Create another task
        store.create_task(title="Task 2", domain="work")

        # Verify again using same pooled connection
        cursor = conn.execute("SELECT COUNT(*) FROM tasks")
        assert cursor.fetchone()[0] == 2
