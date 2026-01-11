"""
Unit tests for Neo4j session leak detection and error handling.

Comprehensive tests to verify:
1. Sessions are properly cleaned up on errors
2. Context manager handles exceptions correctly
3. No sessions are leaked under any circumstances
"""

import pytest
from unittest.mock import AsyncMock, Mock, MagicMock, call
import sys


# Mock neo4j before importing the adapter
mock_neo4j = MagicMock()
sys.modules['neo4j'] = mock_neo4j


class TestSessionLeakDetection:
    """Test for session leaks under various error conditions."""

    @pytest.mark.asyncio
    async def test_no_leak_on_single_exception(self):
        """Verify single exception doesn't leak session."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext

        mock_adapter = Mock()
        mock_session = AsyncMock()
        mock_adapter._driver = Mock()
        mock_adapter._driver.session = Mock(return_value=mock_session)

        context = Neo4jSessionContext(mock_adapter)

        # Track close calls
        close_call_count = 0
        original_close = mock_session.close

        async def track_close():
            nonlocal close_call_count
            close_call_count += 1
            await original_close()

        mock_session.close = track_close

        # Use context with exception
        with pytest.raises(RuntimeError):
            async with context:
                raise RuntimeError("Test error")

        # Verify session was closed exactly once
        assert close_call_count == 1

    @pytest.mark.asyncio
    async def test_no_leak_on_multiple_consecutive_failures(self):
        """Verify multiple consecutive failures don't leak sessions."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext

        mock_adapter = Mock()
        sessions_created = []
        sessions_closed = []

        def create_session(*args, **kwargs):
            session = AsyncMock()
            sessions_created.append(session)

            async def track_close():
                sessions_closed.append(session)

            session.close = track_close
            return session

        mock_adapter._driver = Mock()
        mock_adapter._driver.session = Mock(side_effect=create_session)

        # Run 5 consecutive operations that fail
        for i in range(5):
            context = Neo4jSessionContext(mock_adapter)

            with pytest.raises(ValueError):
                async with context:
                    raise ValueError(f"Error {i}")

        # Verify all sessions were closed
        assert len(sessions_created) == 5
        assert len(sessions_closed) == 5
        assert set(sessions_created) == set(sessions_closed)

    @pytest.mark.asyncio
    async def test_no_leak_when_close_fails(self):
        """Verify no leak even when session.close() fails."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext

        mock_adapter = Mock()
        mock_session = AsyncMock()

        # Make close() fail
        mock_session.close = AsyncMock(side_effect=Exception("Close failed"))

        mock_adapter._driver = Mock()
        mock_adapter._driver.session = Mock(return_value=mock_session)

        context = Neo4jSessionContext(mock_adapter)

        # Enter and exit context
        await context.__aenter__()

        # Exit should propagate close exception
        with pytest.raises(Exception, match="Close failed"):
            await context.__aexit__(None, None, None)

        # Verify close was attempted
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_leak_with_transaction_commit_failure(self):
        """Verify no leak when transaction commit fails."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext

        mock_adapter = Mock()
        mock_session = AsyncMock()
        mock_transaction = AsyncMock()

        # Make commit fail
        mock_transaction.commit = AsyncMock(side_effect=Exception("Commit failed"))
        mock_session.begin_transaction = AsyncMock(return_value=mock_transaction)

        mock_adapter._driver = Mock()
        mock_adapter._driver.session = Mock(return_value=mock_session)

        context = Neo4jSessionContext(mock_adapter, batch_transaction=True)

        # Enter context
        await context.__aenter__()

        # Exit should propagate commit exception but still close session
        with pytest.raises(Exception, match="Commit failed"):
            await context.__aexit__(None, None, None)

        # Verify session was closed despite commit failure
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_leak_with_transaction_rollback_failure(self):
        """Verify no leak when transaction rollback fails."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext

        mock_adapter = Mock()
        mock_session = AsyncMock()
        mock_transaction = AsyncMock()

        # Make rollback fail
        mock_transaction.rollback = AsyncMock(side_effect=Exception("Rollback failed"))
        mock_session.begin_transaction = AsyncMock(return_value=mock_transaction)

        mock_adapter._driver = Mock()
        mock_adapter._driver.session = Mock(return_value=mock_session)

        context = Neo4jSessionContext(mock_adapter, batch_transaction=True)

        # Enter context
        await context.__aenter__()

        # Exit with error should propagate rollback exception but still close session
        with pytest.raises(Exception, match="Rollback failed"):
            await context.__aexit__(ValueError, ValueError("Original"), None)

        # Verify session was closed despite rollback failure
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_leak_with_both_rollback_and_close_failures(self):
        """Verify proper cleanup when both rollback and close fail."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext

        mock_adapter = Mock()
        mock_session = AsyncMock()
        mock_transaction = AsyncMock()

        # Make both rollback and close fail
        mock_transaction.rollback = AsyncMock(side_effect=Exception("Rollback failed"))
        mock_session.close = AsyncMock(side_effect=Exception("Close failed"))
        mock_session.begin_transaction = AsyncMock(return_value=mock_transaction)

        mock_adapter._driver = Mock()
        mock_adapter._driver.session = Mock(return_value=mock_session)

        context = Neo4jSessionContext(mock_adapter, batch_transaction=True)

        # Enter context
        await context.__aenter__()

        # Exit should attempt both operations
        # The rollback exception should be raised first (from try block)
        with pytest.raises(Exception, match="Rollback failed"):
            await context.__aexit__(ValueError, ValueError("Original"), None)

        # Verify both operations were attempted
        mock_transaction.rollback.assert_called_once()
        mock_session.close.assert_called_once()


class TestExceptionHandling:
    """Test exception handling and propagation."""

    @pytest.mark.asyncio
    async def test_exception_propagates_correctly(self):
        """Verify exceptions propagate correctly through context manager."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext

        mock_adapter = Mock()
        mock_session = AsyncMock()
        mock_adapter._driver = Mock()
        mock_adapter._driver.session = Mock(return_value=mock_session)

        context = Neo4jSessionContext(mock_adapter)

        # Verify specific exception propagates
        with pytest.raises(ValueError, match="Specific error"):
            async with context:
                raise ValueError("Specific error")

    @pytest.mark.asyncio
    async def test_exception_type_preserved(self):
        """Verify exception type is preserved through context manager."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext

        mock_adapter = Mock()
        mock_session = AsyncMock()
        mock_adapter._driver = Mock()
        mock_adapter._driver.session = Mock(return_value=mock_session)

        context = Neo4jSessionContext(mock_adapter)

        # Test different exception types
        custom_exception = TypeError("Custom type error")

        with pytest.raises(TypeError) as exc_info:
            async with context:
                raise custom_exception

        assert exc_info.value is custom_exception

    @pytest.mark.asyncio
    async def test_nested_exceptions_handled_correctly(self):
        """Verify nested exceptions are handled correctly."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext

        mock_adapter = Mock()
        mock_session = AsyncMock()
        mock_transaction = AsyncMock()

        # User exception
        user_error = ValueError("User error")

        # Rollback also fails with different exception
        mock_transaction.rollback = AsyncMock(side_effect=RuntimeError("Rollback failed"))
        mock_session.begin_transaction = AsyncMock(return_value=mock_transaction)

        mock_adapter._driver = Mock()
        mock_adapter._driver.session = Mock(return_value=mock_session)

        context = Neo4jSessionContext(mock_adapter, batch_transaction=True)

        # The rollback exception should be raised (from __aexit__)
        with pytest.raises(RuntimeError, match="Rollback failed"):
            async with context:
                raise user_error

        # Verify rollback was attempted
        mock_transaction.rollback.assert_called_once()
        # Verify session was closed
        mock_session.close.assert_called_once()


class TestSessionLifecycleTracking:
    """Test session lifecycle tracking to detect leaks."""

    @pytest.mark.asyncio
    async def test_session_lifecycle_single_context(self):
        """Track complete session lifecycle for single context."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext

        mock_adapter = Mock()
        mock_session = AsyncMock()
        mock_adapter._driver = Mock()
        mock_adapter._driver.session = Mock(return_value=mock_session)

        lifecycle_events = []

        # Track session creation
        original_session_call = mock_adapter._driver.session
        def track_creation(*args, **kwargs):
            lifecycle_events.append("session_created")
            return original_session_call(*args, **kwargs)
        mock_adapter._driver.session = Mock(side_effect=track_creation)

        # Track session close
        original_close = mock_session.close
        async def track_close():
            lifecycle_events.append("session_closed")
            await original_close()
        mock_session.close = track_close

        context = Neo4jSessionContext(mock_adapter)

        # Use context
        async with context:
            lifecycle_events.append("in_context")

        # Verify lifecycle order
        assert lifecycle_events == ["session_created", "in_context", "session_closed"]

    @pytest.mark.asyncio
    async def test_session_lifecycle_with_transaction(self):
        """Track complete session lifecycle with transaction."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext

        mock_adapter = Mock()
        mock_session = AsyncMock()
        mock_transaction = AsyncMock()
        mock_session.begin_transaction = AsyncMock(return_value=mock_transaction)
        mock_adapter._driver = Mock()
        mock_adapter._driver.session = Mock(return_value=mock_session)

        lifecycle_events = []

        # Track all operations
        original_session_call = mock_adapter._driver.session
        def track_creation(*args, **kwargs):
            lifecycle_events.append("session_created")
            return original_session_call(*args, **kwargs)
        mock_adapter._driver.session = Mock(side_effect=track_creation)

        original_begin = mock_session.begin_transaction
        async def track_begin():
            lifecycle_events.append("transaction_begin")
            return await original_begin()
        mock_session.begin_transaction = track_begin

        original_commit = mock_transaction.commit
        async def track_commit():
            lifecycle_events.append("transaction_commit")
            await original_commit()
        mock_transaction.commit = track_commit

        original_close = mock_session.close
        async def track_close():
            lifecycle_events.append("session_closed")
            await original_close()
        mock_session.close = track_close

        context = Neo4jSessionContext(mock_adapter, batch_transaction=True)

        # Use context
        async with context:
            lifecycle_events.append("in_context")

        # Verify lifecycle order
        expected = [
            "session_created",
            "transaction_begin",
            "in_context",
            "transaction_commit",
            "session_closed"
        ]
        assert lifecycle_events == expected

    @pytest.mark.asyncio
    async def test_session_lifecycle_with_error(self):
        """Track session lifecycle when error occurs."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext

        mock_adapter = Mock()
        mock_session = AsyncMock()
        mock_transaction = AsyncMock()
        mock_session.begin_transaction = AsyncMock(return_value=mock_transaction)
        mock_adapter._driver = Mock()
        mock_adapter._driver.session = Mock(return_value=mock_session)

        lifecycle_events = []

        # Track operations
        original_session_call = mock_adapter._driver.session
        def track_creation(*args, **kwargs):
            lifecycle_events.append("session_created")
            return original_session_call(*args, **kwargs)
        mock_adapter._driver.session = Mock(side_effect=track_creation)

        original_begin = mock_session.begin_transaction
        async def track_begin():
            lifecycle_events.append("transaction_begin")
            return await original_begin()
        mock_session.begin_transaction = track_begin

        original_rollback = mock_transaction.rollback
        async def track_rollback():
            lifecycle_events.append("transaction_rollback")
            await original_rollback()
        mock_transaction.rollback = track_rollback

        original_close = mock_session.close
        async def track_close():
            lifecycle_events.append("session_closed")
            await original_close()
        mock_session.close = track_close

        context = Neo4jSessionContext(mock_adapter, batch_transaction=True)

        # Use context with error
        with pytest.raises(ValueError):
            async with context:
                lifecycle_events.append("in_context")
                raise ValueError("Test error")

        # Verify lifecycle order with rollback
        expected = [
            "session_created",
            "transaction_begin",
            "in_context",
            "transaction_rollback",
            "session_closed"
        ]
        assert lifecycle_events == expected


class TestResourceCleanupGuarantees:
    """Test that resources are always cleaned up."""

    @pytest.mark.asyncio
    async def test_cleanup_guaranteed_with_try_finally(self):
        """Verify cleanup uses try-finally pattern."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext
        import inspect

        # Get __aexit__ source to verify try-finally usage
        source = inspect.getsource(Neo4jSessionContext.__aexit__)

        # Verify it uses try-finally pattern
        assert "try:" in source
        assert "finally:" in source
        # Verify session close is in finally block
        assert "self._session" in source and "close" in source

    @pytest.mark.asyncio
    async def test_cleanup_called_even_with_keyboard_interrupt(self):
        """Verify cleanup happens even with KeyboardInterrupt."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext

        mock_adapter = Mock()
        mock_session = AsyncMock()
        mock_adapter._driver = Mock()
        mock_adapter._driver.session = Mock(return_value=mock_session)

        context = Neo4jSessionContext(mock_adapter)

        # Use context with KeyboardInterrupt
        with pytest.raises(KeyboardInterrupt):
            async with context:
                raise KeyboardInterrupt()

        # Verify session was closed even for KeyboardInterrupt
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_called_even_with_system_exit(self):
        """Verify cleanup happens even with SystemExit."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext

        mock_adapter = Mock()
        mock_session = AsyncMock()
        mock_adapter._driver = Mock()
        mock_adapter._driver.session = Mock(return_value=mock_session)

        context = Neo4jSessionContext(mock_adapter)

        # Use context with SystemExit
        with pytest.raises(SystemExit):
            async with context:
                raise SystemExit(1)

        # Verify session was closed even for SystemExit
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_contexts_isolated_cleanup(self):
        """Verify multiple contexts have isolated cleanup."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext

        mock_adapter = Mock()

        # Create separate sessions
        sessions = []
        def create_session(*args, **kwargs):
            session = AsyncMock()
            sessions.append(session)
            return session

        mock_adapter._driver = Mock()
        mock_adapter._driver.session = Mock(side_effect=create_session)

        # Use multiple contexts
        context1 = Neo4jSessionContext(mock_adapter)
        async with context1:
            pass

        context2 = Neo4jSessionContext(mock_adapter)
        async with context2:
            pass

        context3 = Neo4jSessionContext(mock_adapter)
        async with context3:
            pass

        # Verify all sessions were created and closed
        assert len(sessions) == 3
        for session in sessions:
            session.close.assert_called_once()


class TestEdgeCaseCleanup:
    """Test cleanup in edge cases."""

    @pytest.mark.asyncio
    async def test_cleanup_when_session_none(self):
        """Verify cleanup handles None session gracefully."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext

        mock_adapter = Mock()
        mock_adapter._driver = Mock()

        context = Neo4jSessionContext(mock_adapter)
        # Don't enter context, so session remains None

        # Exit should handle None session without error
        result = await context.__aexit__(None, None, None)
        assert result is False

    @pytest.mark.asyncio
    async def test_cleanup_when_transaction_none_in_batch_mode(self):
        """Verify cleanup handles None transaction in batch mode."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext

        mock_adapter = Mock()
        mock_session = AsyncMock()
        mock_adapter._driver = Mock()
        mock_adapter._driver.session = Mock(return_value=mock_session)

        context = Neo4jSessionContext(mock_adapter, batch_transaction=True)

        # Manually set session but not transaction
        context._session = mock_session
        context._transaction = None

        # Exit should handle None transaction gracefully
        result = await context.__aexit__(None, None, None)
        assert result is False

        # Session should still be closed
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_double_exit_idempotent(self):
        """Verify calling __aexit__ multiple times is safe."""
        from Tools.adapters.neo4j_adapter import Neo4jSessionContext

        mock_adapter = Mock()
        mock_session = AsyncMock()
        mock_adapter._driver = Mock()
        mock_adapter._driver.session = Mock(return_value=mock_session)

        context = Neo4jSessionContext(mock_adapter)
        await context.__aenter__()

        # First exit
        await context.__aexit__(None, None, None)

        # Verify session closed once
        assert mock_session.close.call_count == 1

        # Second exit (should be safe even though session already None)
        context._session = None
        await context.__aexit__(None, None, None)

        # Should still be just one close call
        assert mock_session.close.call_count == 1
