"""
Unit tests for Neo4j session pooling (Neo4jSessionContext).

Tests the Neo4jSessionContext class for session lifecycle management,
error handling, transaction batching, and cleanup.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock, call
import sys


# Mock neo4j before importing the adapter
mock_neo4j = MagicMock()
sys.modules['neo4j'] = mock_neo4j


class TestNeo4jSessionContextImports:
    """Test Neo4jSessionContext can be imported."""

    def test_import_session_context(self):
        """Test Neo4jSessionContext can be imported."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext
        assert Neo4jSessionContext is not None

    def test_import_neo4j_available_flag(self):
        """Test NEO4J_AVAILABLE flag is defined."""
        from Tools.adapters.neo4j_adapter import NEO4J_AVAILABLE
        assert isinstance(NEO4J_AVAILABLE, bool)


class TestNeo4jSessionContextInitialization:
    """Test Neo4jSessionContext initialization."""

    def test_init_default_database(self):
        """Test initialization with default database."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext

        mock_adapter = Mock()
        mock_adapter._driver = Mock()

        context = Neo4jSessionContext(mock_adapter)

        assert context._adapter is mock_adapter
        assert context._database == "neo4j"
        assert context._batch_transaction is False
        assert context._session is None
        assert context._transaction is None

    def test_init_custom_database(self):
        """Test initialization with custom database name."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext

        mock_adapter = Mock()
        mock_adapter._driver = Mock()

        context = Neo4jSessionContext(mock_adapter, database="custom_db")

        assert context._database == "custom_db"

    def test_init_batch_transaction_enabled(self):
        """Test initialization with batch transaction enabled."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext

        mock_adapter = Mock()
        mock_adapter._driver = Mock()

        context = Neo4jSessionContext(mock_adapter, batch_transaction=True)

        assert context._batch_transaction is True


class TestNeo4jSessionContextLifecycle:
    """Test Neo4jSessionContext async context manager lifecycle."""

    @pytest.mark.asyncio
    async def test_aenter_creates_session_without_transaction(self):
        """Test __aenter__ creates session in non-batch mode."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext

        mock_adapter = Mock()
        mock_session = Mock()
        mock_adapter._driver = Mock()
        mock_adapter._driver.session = Mock(return_value=mock_session)

        context = Neo4jSessionContext(mock_adapter, database="neo4j", batch_transaction=False)

        result = await context.__aenter__()

        # Verify session was created with correct database
        mock_adapter._driver.session.assert_called_once_with(database="neo4j")
        # Verify session is stored
        assert context._session is mock_session
        # Verify session is returned (not transaction)
        assert result is mock_session
        # Verify no transaction created
        assert context._transaction is None

    @pytest.mark.asyncio
    async def test_aenter_creates_session_with_transaction(self):
        """Test __aenter__ creates session and begins transaction in batch mode."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext

        mock_adapter = Mock()
        mock_session = AsyncMock()
        mock_transaction = Mock()
        mock_session.begin_transaction = AsyncMock(return_value=mock_transaction)
        mock_adapter._driver = Mock()
        mock_adapter._driver.session = Mock(return_value=mock_session)

        context = Neo4jSessionContext(mock_adapter, batch_transaction=True)

        result = await context.__aenter__()

        # Verify session was created
        mock_adapter._driver.session.assert_called_once_with(database="neo4j")
        # Verify transaction was started
        mock_session.begin_transaction.assert_called_once()
        # Verify transaction is stored
        assert context._transaction is mock_transaction
        # Verify transaction is returned (not session)
        assert result is mock_transaction

    @pytest.mark.asyncio
    async def test_aexit_closes_session_without_transaction(self):
        """Test __aexit__ closes session in non-batch mode."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext

        mock_adapter = Mock()
        mock_session = AsyncMock()
        mock_adapter._driver = Mock()
        mock_adapter._driver.session = Mock(return_value=mock_session)

        context = Neo4jSessionContext(mock_adapter, batch_transaction=False)
        await context.__aenter__()

        # Exit without exception
        result = await context.__aexit__(None, None, None)

        # Verify session was closed
        mock_session.close.assert_called_once()
        # Verify exception is not suppressed
        assert result is False

    @pytest.mark.asyncio
    async def test_aexit_commits_transaction_on_success(self):
        """Test __aexit__ commits transaction when no exception occurs."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext

        mock_adapter = Mock()
        mock_session = AsyncMock()
        mock_transaction = AsyncMock()
        mock_session.begin_transaction = AsyncMock(return_value=mock_transaction)
        mock_adapter._driver = Mock()
        mock_adapter._driver.session = Mock(return_value=mock_session)

        context = Neo4jSessionContext(mock_adapter, batch_transaction=True)
        await context.__aenter__()

        # Exit without exception
        result = await context.__aexit__(None, None, None)

        # Verify transaction was committed
        mock_transaction.commit.assert_called_once()
        # Verify transaction was not rolled back
        mock_transaction.rollback.assert_not_called()
        # Verify session was closed
        mock_session.close.assert_called_once()
        # Verify exception is not suppressed
        assert result is False

    @pytest.mark.asyncio
    async def test_aexit_rolls_back_transaction_on_exception(self):
        """Test __aexit__ rolls back transaction when exception occurs."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext

        mock_adapter = Mock()
        mock_session = AsyncMock()
        mock_transaction = AsyncMock()
        mock_session.begin_transaction = AsyncMock(return_value=mock_transaction)
        mock_adapter._driver = Mock()
        mock_adapter._driver.session = Mock(return_value=mock_session)

        context = Neo4jSessionContext(mock_adapter, batch_transaction=True)
        await context.__aenter__()

        # Exit with exception
        exc_type = ValueError
        exc_val = ValueError("Test error")
        exc_tb = None
        result = await context.__aexit__(exc_type, exc_val, exc_tb)

        # Verify transaction was rolled back
        mock_transaction.rollback.assert_called_once()
        # Verify transaction was not committed
        mock_transaction.commit.assert_not_called()
        # Verify session was closed
        mock_session.close.assert_called_once()
        # Verify exception is not suppressed
        assert result is False


class TestNeo4jSessionContextErrorHandling:
    """Test Neo4jSessionContext error handling and cleanup."""

    @pytest.mark.asyncio
    async def test_session_cleanup_even_if_commit_fails(self):
        """Test session is closed even if transaction commit fails."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext

        mock_adapter = Mock()
        mock_session = AsyncMock()
        mock_transaction = AsyncMock()
        mock_transaction.commit = AsyncMock(side_effect=Exception("Commit failed"))
        mock_session.begin_transaction = AsyncMock(return_value=mock_transaction)
        mock_adapter._driver = Mock()
        mock_adapter._driver.session = Mock(return_value=mock_session)

        context = Neo4jSessionContext(mock_adapter, batch_transaction=True)
        await context.__aenter__()

        # Exit should raise commit exception but still close session
        with pytest.raises(Exception, match="Commit failed"):
            await context.__aexit__(None, None, None)

        # Verify session was still closed despite commit failure
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_cleanup_even_if_rollback_fails(self):
        """Test session is closed even if transaction rollback fails."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext

        mock_adapter = Mock()
        mock_session = AsyncMock()
        mock_transaction = AsyncMock()
        mock_transaction.rollback = AsyncMock(side_effect=Exception("Rollback failed"))
        mock_session.begin_transaction = AsyncMock(return_value=mock_transaction)
        mock_adapter._driver = Mock()
        mock_adapter._driver.session = Mock(return_value=mock_session)

        context = Neo4jSessionContext(mock_adapter, batch_transaction=True)
        await context.__aenter__()

        # Exit with exception should raise rollback exception but still close session
        with pytest.raises(Exception, match="Rollback failed"):
            await context.__aexit__(ValueError, ValueError("Original error"), None)

        # Verify session was still closed despite rollback failure
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_exception_not_suppressed(self):
        """Test that exceptions are not suppressed by context manager."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext

        mock_adapter = Mock()
        mock_session = AsyncMock()
        mock_adapter._driver = Mock()
        mock_adapter._driver.session = Mock(return_value=mock_session)

        context = Neo4jSessionContext(mock_adapter, batch_transaction=False)

        # Use context manager and verify exception propagates
        with pytest.raises(ValueError, match="Test exception"):
            async with context:
                raise ValueError("Test exception")

        # Verify session was closed
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_cleanup_on_user_exception(self):
        """Test session cleanup happens when user code raises exception."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext

        mock_adapter = Mock()
        mock_session = AsyncMock()
        mock_transaction = AsyncMock()
        mock_session.begin_transaction = AsyncMock(return_value=mock_transaction)
        mock_adapter._driver = Mock()
        mock_adapter._driver.session = Mock(return_value=mock_session)

        context = Neo4jSessionContext(mock_adapter, batch_transaction=True)

        with pytest.raises(RuntimeError, match="User error"):
            async with context:
                raise RuntimeError("User error")

        # Verify transaction was rolled back
        mock_transaction.rollback.assert_called_once()
        # Verify session was closed
        mock_session.close.assert_called_once()


class TestNeo4jSessionContextIntegration:
    """Test Neo4jSessionContext integration scenarios."""

    @pytest.mark.asyncio
    async def test_full_lifecycle_without_transaction(self):
        """Test complete lifecycle in session reuse mode."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext

        mock_adapter = Mock()
        mock_session = AsyncMock()
        mock_adapter._driver = Mock()
        mock_adapter._driver.session = Mock(return_value=mock_session)

        context = Neo4jSessionContext(mock_adapter, batch_transaction=False)

        # Enter context
        session = await context.__aenter__()
        assert session is mock_session
        assert context._session is mock_session
        assert context._transaction is None

        # Exit context
        result = await context.__aexit__(None, None, None)
        assert result is False
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_full_lifecycle_with_transaction_success(self):
        """Test complete lifecycle in batch transaction mode (success)."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext

        mock_adapter = Mock()
        mock_session = AsyncMock()
        mock_transaction = AsyncMock()
        mock_session.begin_transaction = AsyncMock(return_value=mock_transaction)
        mock_adapter._driver = Mock()
        mock_adapter._driver.session = Mock(return_value=mock_session)

        context = Neo4jSessionContext(mock_adapter, batch_transaction=True)

        # Enter context
        tx = await context.__aenter__()
        assert tx is mock_transaction
        assert context._session is mock_session
        assert context._transaction is mock_transaction
        mock_session.begin_transaction.assert_called_once()

        # Exit context (success)
        result = await context.__aexit__(None, None, None)
        assert result is False
        mock_transaction.commit.assert_called_once()
        mock_transaction.rollback.assert_not_called()
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_full_lifecycle_with_transaction_failure(self):
        """Test complete lifecycle in batch transaction mode (failure)."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext

        mock_adapter = Mock()
        mock_session = AsyncMock()
        mock_transaction = AsyncMock()
        mock_session.begin_transaction = AsyncMock(return_value=mock_transaction)
        mock_adapter._driver = Mock()
        mock_adapter._driver.session = Mock(return_value=mock_session)

        context = Neo4jSessionContext(mock_adapter, batch_transaction=True)

        # Enter context
        await context.__aenter__()

        # Exit context (with error)
        exc_type = RuntimeError
        exc_val = RuntimeError("Operation failed")
        result = await context.__aexit__(exc_type, exc_val, None)

        assert result is False
        mock_transaction.rollback.assert_called_once()
        mock_transaction.commit.assert_not_called()
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_with_statement(self):
        """Test using context manager with async with statement."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext

        mock_adapter = Mock()
        mock_session = AsyncMock()
        mock_adapter._driver = Mock()
        mock_adapter._driver.session = Mock(return_value=mock_session)

        context = Neo4jSessionContext(mock_adapter)

        # Use with statement
        async with context as session:
            assert session is mock_session
            # Session should be active here
            assert context._session is mock_session

        # After exiting, session should be closed
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_with_transaction_and_exception(self):
        """Test using context manager with transaction when exception occurs."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext

        mock_adapter = Mock()
        mock_session = AsyncMock()
        mock_transaction = AsyncMock()
        mock_session.begin_transaction = AsyncMock(return_value=mock_transaction)
        mock_adapter._driver = Mock()
        mock_adapter._driver.session = Mock(return_value=mock_session)

        context = Neo4jSessionContext(mock_adapter, batch_transaction=True)

        # Use with statement that raises exception
        with pytest.raises(ValueError, match="Test error"):
            async with context as tx:
                assert tx is mock_transaction
                raise ValueError("Test error")

        # Transaction should be rolled back
        mock_transaction.rollback.assert_called_once()
        mock_transaction.commit.assert_not_called()
        # Session should be closed
        mock_session.close.assert_called_once()


class TestNeo4jSessionContextNestedScenarios:
    """Test nested context scenarios and edge cases."""

    @pytest.mark.asyncio
    async def test_multiple_sequential_contexts(self):
        """Test using multiple sequential contexts."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext

        mock_adapter = Mock()
        mock_session1 = AsyncMock()
        mock_session2 = AsyncMock()
        mock_adapter._driver = Mock()

        # Different sessions for each context
        call_count = 0
        def get_session(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return mock_session1 if call_count == 1 else mock_session2

        mock_adapter._driver.session = Mock(side_effect=get_session)

        # First context
        context1 = Neo4jSessionContext(mock_adapter)
        async with context1 as session1:
            assert session1 is mock_session1

        # Second context
        context2 = Neo4jSessionContext(mock_adapter)
        async with context2 as session2:
            assert session2 is mock_session2

        # Both sessions should be closed
        mock_session1.close.assert_called_once()
        mock_session2.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_state_isolation(self):
        """Test that different context instances have isolated state."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext

        mock_adapter = Mock()
        mock_session1 = AsyncMock()
        mock_session2 = AsyncMock()

        call_count = 0
        def get_session(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return mock_session1 if call_count == 1 else mock_session2

        mock_adapter._driver = Mock(side_effect=get_session)

        context1 = Neo4jSessionContext(mock_adapter, batch_transaction=True)
        context2 = Neo4jSessionContext(mock_adapter, batch_transaction=False)

        # Verify isolated initialization
        assert context1._batch_transaction is True
        assert context2._batch_transaction is False
        assert context1._session is None
        assert context2._session is None
        assert context1._transaction is None
        assert context2._transaction is None


class TestNeo4jSessionContextEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_aexit_when_session_is_none(self):
        """Test __aexit__ handles case where session is None."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext

        mock_adapter = Mock()
        mock_adapter._driver = Mock()

        context = Neo4jSessionContext(mock_adapter)
        # Don't enter context, so _session remains None

        # Exit should not fail even though session is None
        result = await context.__aexit__(None, None, None)
        assert result is False

    @pytest.mark.asyncio
    async def test_aexit_when_transaction_is_none_but_batch_mode(self):
        """Test __aexit__ handles None transaction in batch mode."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext

        mock_adapter = Mock()
        mock_session = AsyncMock()
        mock_adapter._driver = Mock()
        mock_adapter._driver.session = Mock(return_value=mock_session)

        context = Neo4jSessionContext(mock_adapter, batch_transaction=True)
        # Manually set session but keep transaction None
        context._session = mock_session
        context._transaction = None

        # Exit should handle None transaction gracefully
        result = await context.__aexit__(None, None, None)
        assert result is False
        # Session should still be closed
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_custom_database_passed_to_driver(self):
        """Test custom database name is passed to driver.session()."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext

        mock_adapter = Mock()
        mock_session = AsyncMock()
        mock_adapter._driver = Mock()
        mock_adapter._driver.session = Mock(return_value=mock_session)

        context = Neo4jSessionContext(mock_adapter, database="mydb")
        await context.__aenter__()

        # Verify custom database was used
        mock_adapter._driver.session.assert_called_once_with(database="mydb")
