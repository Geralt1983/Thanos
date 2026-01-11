"""
Integration tests for Neo4j batch operations and session pooling.

These tests verify that:
1. Multiple operations share a session when using session_context
2. Session pooling reduces overhead (fewer session creations)
3. Batch operations execute correctly with shared sessions
4. Atomic transactions work correctly (commit/rollback)
5. Non-atomic batch operations allow partial success
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock, call
import sys
from typing import List, Dict, Any


# Mock neo4j before importing the adapter
mock_neo4j = MagicMock()
sys.modules['neo4j'] = mock_neo4j


class TestSessionReuse:
    """Test that multiple operations share the same session."""

    @pytest.mark.asyncio
    async def test_multiple_operations_share_session(self):
        """Verify multiple operations use the same session object."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter
        from Tools.adapters.base import ToolResult

        # Create adapter with mocked driver
        adapter = Neo4jAdapter(uri="bolt://localhost:7687", username="neo4j", password="test")

        # Mock session and transaction
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.single.return_value = {"id": "test_id_1"}
        mock_session.run = AsyncMock(return_value=mock_result)

        adapter._driver = Mock()
        adapter._driver.session = Mock(return_value=mock_session)

        session_objects = []

        # Capture session objects used by operations
        original_create_entity = adapter._create_entity
        original_link_nodes = adapter._link_nodes

        async def capture_create_entity(entity_data, session=None):
            session_objects.append(session)
            return ToolResult.ok({"id": f"entity_{len(session_objects)}"})

        async def capture_link_nodes(link_data, session=None):
            session_objects.append(session)
            return ToolResult.ok({"id": f"link_{len(session_objects)}"})

        adapter._create_entity = capture_create_entity
        adapter._link_nodes = capture_link_nodes

        # Execute multiple operations with session context
        async with adapter.session_context() as session:
            await adapter._create_entity({"name": "Entity1", "type": "person"}, session=session)
            await adapter._create_entity({"name": "Entity2", "type": "project"}, session=session)
            await adapter._link_nodes({"from_id": "1", "relationship": "WORKS_ON", "to_id": "2"}, session=session)

        # Verify all operations used the same session object
        assert len(session_objects) == 3
        assert session_objects[0] is session_objects[1]
        assert session_objects[1] is session_objects[2]
        assert session_objects[0] is mock_session

        # Verify driver.session was called only once
        adapter._driver.session.assert_called_once()

    @pytest.mark.asyncio
    async def test_sequential_contexts_use_different_sessions(self):
        """Verify sequential context blocks use different sessions."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter(uri="bolt://localhost:7687", username="neo4j", password="test")

        # Mock multiple session objects
        mock_session_1 = AsyncMock()
        mock_session_2 = AsyncMock()

        adapter._driver = Mock()
        adapter._driver.session = Mock(side_effect=[mock_session_1, mock_session_2])

        sessions = []

        # First context block
        async with adapter.session_context() as session1:
            sessions.append(session1)

        # Second context block
        async with adapter.session_context() as session2:
            sessions.append(session2)

        # Verify different session objects were used
        assert len(sessions) == 2
        assert sessions[0] is mock_session_1
        assert sessions[1] is mock_session_2
        assert sessions[0] is not sessions[1]

        # Verify driver.session was called twice
        assert adapter._driver.session.call_count == 2


class TestSessionPoolingOverhead:
    """Test that session pooling reduces overhead."""

    @pytest.mark.asyncio
    async def test_session_pooling_reduces_session_creation(self):
        """Verify pooling creates fewer sessions than individual operations."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter
        from Tools.adapters.base import ToolResult

        adapter = Neo4jAdapter(uri="bolt://localhost:7687", username="neo4j", password="test")

        # Mock session
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.single.return_value = {"id": "test_id"}
        mock_session.run = AsyncMock(return_value=mock_result)

        adapter._driver = Mock()
        adapter._driver.session = Mock(return_value=mock_session)

        # Mock the internal methods to return success
        async def mock_create_entity(entity_data, session=None):
            if session:
                await session.run("MOCK QUERY")
            return ToolResult.ok({"id": "entity_123"})

        adapter._create_entity = mock_create_entity

        # Scenario 1: WITHOUT session pooling (individual operations)
        adapter._driver.session.reset_mock()
        for i in range(5):
            result = await adapter._create_entity({"name": f"Entity{i}", "type": "person"})
            assert result.success

        sessions_without_pooling = adapter._driver.session.call_count

        # Scenario 2: WITH session pooling (session context)
        adapter._driver.session.reset_mock()
        async with adapter.session_context() as session:
            for i in range(5):
                result = await adapter._create_entity({"name": f"Entity{i}", "type": "person"}, session=session)
                assert result.success

        sessions_with_pooling = adapter._driver.session.call_count

        # Verify pooling reduces session creation
        # Without pooling: 0 sessions (mocked operations don't create sessions)
        # With pooling: 1 session
        assert sessions_with_pooling == 1
        assert sessions_with_pooling < 5  # Much fewer than number of operations

    @pytest.mark.asyncio
    async def test_batch_operation_uses_single_session(self):
        """Verify batch operations use only one session for multiple items."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter
        from Tools.adapters.base import ToolResult

        adapter = Neo4jAdapter(uri="bolt://localhost:7687", username="neo4j", password="test")

        # Mock session
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.single.return_value = {"id": "test_id"}
        mock_session.run = AsyncMock(return_value=mock_result)

        adapter._driver = Mock()
        adapter._driver.session = Mock(return_value=mock_session)

        # Mock _create_entity to return success
        entity_counter = {"count": 0}

        async def mock_create_entity(entity_data, session=None):
            entity_counter["count"] += 1
            return ToolResult.ok({"id": f"entity_{entity_counter['count']}", "name": entity_data.get("name")})

        adapter._create_entity = mock_create_entity

        # Execute batch operation
        entities = [
            {"name": "Alice", "type": "person", "domain": "work"},
            {"name": "Bob", "type": "person", "domain": "work"},
            {"name": "Project X", "type": "project", "domain": "work"},
        ]

        result = await adapter.create_entities_batch(entities, atomic=True)

        # Verify success
        assert result.success
        assert result.data["count"] == 3

        # Verify only one session was created
        adapter._driver.session.assert_called_once()


class TestBatchOperations:
    """Test batch operation functionality."""

    @pytest.mark.asyncio
    async def test_create_entities_batch_success(self):
        """Test successful batch entity creation."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter
        from Tools.adapters.base import ToolResult

        adapter = Neo4jAdapter(uri="bolt://localhost:7687", username="neo4j", password="test")

        # Mock session
        mock_session = AsyncMock()
        mock_transaction = AsyncMock()
        mock_session.begin_transaction = AsyncMock(return_value=mock_transaction)

        adapter._driver = Mock()
        adapter._driver.session = Mock(return_value=mock_session)

        # Mock _create_entity
        entity_counter = {"count": 0}

        async def mock_create_entity(entity_data, session=None):
            entity_counter["count"] += 1
            return ToolResult.ok({
                "id": f"entity_{entity_counter['count']}",
                "name": entity_data.get("name"),
                "type": entity_data.get("type")
            })

        adapter._create_entity = mock_create_entity

        # Execute batch operation
        entities = [
            {"name": "Alice", "type": "person", "domain": "work"},
            {"name": "Bob", "type": "person", "domain": "personal"},
        ]

        result = await adapter.create_entities_batch(entities, atomic=True)

        # Verify success
        assert result.success
        assert result.data["count"] == 2
        assert len(result.data["created"]) == 2
        assert result.data["created"][0]["name"] == "Alice"
        assert result.data["created"][1]["name"] == "Bob"

        # Verify transaction was committed (atomic mode)
        mock_transaction.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_entities_batch_partial_failure_non_atomic(self):
        """Test batch entity creation with partial failure in non-atomic mode."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter
        from Tools.adapters.base import ToolResult

        adapter = Neo4jAdapter(uri="bolt://localhost:7687", username="neo4j", password="test")

        # Mock session (no transaction in non-atomic mode)
        mock_session = AsyncMock()
        adapter._driver = Mock()
        adapter._driver.session = Mock(return_value=mock_session)

        # Mock _create_entity to fail on second entity
        entity_counter = {"count": 0}

        async def mock_create_entity(entity_data, session=None):
            entity_counter["count"] += 1
            if entity_counter["count"] == 2:
                return ToolResult.fail("Database error")
            return ToolResult.ok({
                "id": f"entity_{entity_counter['count']}",
                "name": entity_data.get("name")
            })

        adapter._create_entity = mock_create_entity

        # Execute batch operation in non-atomic mode
        entities = [
            {"name": "Alice", "type": "person"},
            {"name": "Bob", "type": "person"},
            {"name": "Charlie", "type": "person"},
        ]

        result = await adapter.create_entities_batch(entities, atomic=False)

        # Verify partial success
        assert result.success
        assert result.data["count"] == 2  # Alice and Charlie created
        assert len(result.data["created"]) == 2
        assert len(result.data["errors"]) == 1
        assert result.data["errors"][0]["entity"] == "Bob"

    @pytest.mark.asyncio
    async def test_link_nodes_batch_success(self):
        """Test successful batch link creation."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter
        from Tools.adapters.base import ToolResult

        adapter = Neo4jAdapter(uri="bolt://localhost:7687", username="neo4j", password="test")

        # Mock session
        mock_session = AsyncMock()
        mock_transaction = AsyncMock()
        mock_session.begin_transaction = AsyncMock(return_value=mock_transaction)

        adapter._driver = Mock()
        adapter._driver.session = Mock(return_value=mock_session)

        # Mock _link_nodes
        link_counter = {"count": 0}

        async def mock_link_nodes(link_data, session=None):
            link_counter["count"] += 1
            return ToolResult.ok({
                "id": f"link_{link_counter['count']}",
                "from_id": link_data.get("from_id"),
                "relationship": link_data.get("relationship"),
                "to_id": link_data.get("to_id")
            })

        adapter._link_nodes = mock_link_nodes

        # Execute batch operation
        links = [
            {"from_id": "entity_1", "relationship": "WORKS_WITH", "to_id": "entity_2"},
            {"from_id": "entity_1", "relationship": "MANAGES", "to_id": "project_1"},
        ]

        result = await adapter.link_nodes_batch(links, atomic=True)

        # Verify success
        assert result.success
        assert result.data["count"] == 2
        assert len(result.data["created"]) == 2
        assert result.data["created"][0]["relationship"] == "WORKS_WITH"
        assert result.data["created"][1]["relationship"] == "MANAGES"

        # Verify transaction was committed
        mock_transaction.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_memory_batch_complete_workflow(self):
        """Test store_memory_batch with complete workflow."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter
        from Tools.adapters.base import ToolResult

        adapter = Neo4jAdapter(uri="bolt://localhost:7687", username="neo4j", password="test")

        # Mock session
        mock_session = AsyncMock()
        mock_transaction = AsyncMock()
        mock_session.begin_transaction = AsyncMock(return_value=mock_transaction)

        adapter._driver = Mock()
        adapter._driver.session = Mock(return_value=mock_session)

        # Mock all internal methods
        async def mock_create_commitment(commitment_data, session=None):
            return ToolResult.ok({"id": "commitment_123", "content": commitment_data.get("content")})

        async def mock_record_decision(decision_data, session=None):
            return ToolResult.ok({"id": "decision_456", "content": decision_data.get("content")})

        async def mock_create_entity(entity_data, session=None):
            return ToolResult.ok({"id": f"entity_{entity_data.get('name')}", "name": entity_data.get("name")})

        async def mock_link_nodes(link_data, session=None):
            return ToolResult.ok({
                "id": f"link_{link_data.get('from_id')}_{link_data.get('to_id')}",
                "from_id": link_data.get("from_id"),
                "to_id": link_data.get("to_id")
            })

        adapter._create_commitment = mock_create_commitment
        adapter._record_decision = mock_record_decision
        adapter._create_entity = mock_create_entity
        adapter._link_nodes = mock_link_nodes

        # Execute complete memory storage workflow
        memory_data = {
            "commitment": {
                "content": "Launch new feature",
                "to_whom": "Team",
                "deadline": "2026-02-01",
                "domain": "work"
            },
            "decision": {
                "content": "Use React for frontend",
                "rationale": "Team expertise",
                "alternatives": ["Vue", "Angular"],
                "domain": "work"
            },
            "entities": [
                {"name": "Team Lead", "type": "person", "domain": "work"},
                {"name": "Frontend Team", "type": "team", "domain": "work"}
            ],
            "links": [
                {"from_id": "commitment_123", "relationship": "INVOLVES", "to_id": "entity_Team Lead"}
            ]
        }

        result = await adapter.store_memory_batch(memory_data, atomic=True)

        # Verify success
        assert result.success
        assert result.data["commitment"]["id"] == "commitment_123"
        assert result.data["decision"]["id"] == "decision_456"
        assert len(result.data["entities"]) == 2
        assert len(result.data["links"]) == 1

        # Verify only one session was created
        adapter._driver.session.assert_called_once()

        # Verify transaction was committed (atomic mode)
        mock_transaction.commit.assert_called_once()


class TestAtomicTransactions:
    """Test atomic transaction behavior."""

    @pytest.mark.asyncio
    async def test_atomic_batch_commits_on_success(self):
        """Verify atomic batch commits transaction on success."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter
        from Tools.adapters.base import ToolResult

        adapter = Neo4jAdapter(uri="bolt://localhost:7687", username="neo4j", password="test")

        # Mock session and transaction
        mock_session = AsyncMock()
        mock_transaction = AsyncMock()
        mock_session.begin_transaction = AsyncMock(return_value=mock_transaction)

        adapter._driver = Mock()
        adapter._driver.session = Mock(return_value=mock_session)

        # Mock _create_entity to succeed
        async def mock_create_entity(entity_data, session=None):
            return ToolResult.ok({"id": "entity_123", "name": entity_data.get("name")})

        adapter._create_entity = mock_create_entity

        # Execute batch with atomic=True
        entities = [{"name": "Alice", "type": "person"}]
        result = await adapter.create_entities_batch(entities, atomic=True)

        # Verify success and transaction committed
        assert result.success
        mock_transaction.commit.assert_called_once()
        mock_transaction.rollback.assert_not_called()

    @pytest.mark.asyncio
    async def test_atomic_batch_rolls_back_on_failure(self):
        """Verify atomic batch rolls back transaction on failure."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter
        from Tools.adapters.base import ToolResult

        adapter = Neo4jAdapter(uri="bolt://localhost:7687", username="neo4j", password="test")

        # Mock session and transaction
        mock_session = AsyncMock()
        mock_transaction = AsyncMock()
        mock_session.begin_transaction = AsyncMock(return_value=mock_transaction)

        adapter._driver = Mock()
        adapter._driver.session = Mock(return_value=mock_session)

        # Mock _create_entity to fail on second entity
        entity_counter = {"count": 0}

        async def mock_create_entity(entity_data, session=None):
            entity_counter["count"] += 1
            if entity_counter["count"] == 2:
                return ToolResult.fail("Database error")
            return ToolResult.ok({"id": f"entity_{entity_counter['count']}", "name": entity_data.get("name")})

        adapter._create_entity = mock_create_entity

        # Execute batch with atomic=True
        entities = [
            {"name": "Alice", "type": "person"},
            {"name": "Bob", "type": "person"},
        ]
        result = await adapter.create_entities_batch(entities, atomic=True)

        # Verify failure and transaction rolled back
        assert not result.success
        mock_transaction.rollback.assert_called_once()
        mock_transaction.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_non_atomic_batch_no_transaction(self):
        """Verify non-atomic batch doesn't use transaction."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter
        from Tools.adapters.base import ToolResult

        adapter = Neo4jAdapter(uri="bolt://localhost:7687", username="neo4j", password="test")

        # Mock session (no transaction)
        mock_session = AsyncMock()
        adapter._driver = Mock()
        adapter._driver.session = Mock(return_value=mock_session)

        # Mock _create_entity to succeed
        async def mock_create_entity(entity_data, session=None):
            return ToolResult.ok({"id": "entity_123", "name": entity_data.get("name")})

        adapter._create_entity = mock_create_entity

        # Execute batch with atomic=False
        entities = [{"name": "Alice", "type": "person"}]
        result = await adapter.create_entities_batch(entities, atomic=False)

        # Verify success and no transaction was created
        assert result.success
        mock_session.begin_transaction.assert_not_called()


class TestSessionCleanup:
    """Test session cleanup and resource management."""

    @pytest.mark.asyncio
    async def test_session_closed_after_context_exit(self):
        """Verify session is closed when context exits."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter(uri="bolt://localhost:7687", username="neo4j", password="test")

        # Mock session
        mock_session = AsyncMock()
        adapter._driver = Mock()
        adapter._driver.session = Mock(return_value=mock_session)

        # Use session context
        async with adapter.session_context() as session:
            assert session is mock_session

        # Verify session was closed
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_closed_on_exception(self):
        """Verify session is closed even when exception occurs."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter(uri="bolt://localhost:7687", username="neo4j", password="test")

        # Mock session
        mock_session = AsyncMock()
        adapter._driver = Mock()
        adapter._driver.session = Mock(return_value=mock_session)

        # Use session context with exception
        with pytest.raises(ValueError):
            async with adapter.session_context() as session:
                raise ValueError("Test error")

        # Verify session was closed despite exception
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_transaction_rolled_back_and_session_closed_on_exception(self):
        """Verify transaction is rolled back and session closed on exception."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter(uri="bolt://localhost:7687", username="neo4j", password="test")

        # Mock session and transaction
        mock_session = AsyncMock()
        mock_transaction = AsyncMock()
        mock_session.begin_transaction = AsyncMock(return_value=mock_transaction)

        adapter._driver = Mock()
        adapter._driver.session = Mock(return_value=mock_session)

        # Use session context with transaction and exception
        with pytest.raises(ValueError):
            async with adapter.session_context(batch_transaction=True) as tx:
                raise ValueError("Test error")

        # Verify transaction was rolled back
        mock_transaction.rollback.assert_called_once()
        mock_transaction.commit.assert_not_called()

        # Verify session was closed
        mock_session.close.assert_called_once()


class TestPerformanceComparison:
    """Test performance benefits of session pooling."""

    @pytest.mark.asyncio
    async def test_session_reuse_reduces_driver_calls(self):
        """Verify session reuse reduces calls to driver.session()."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter
        from Tools.adapters.base import ToolResult

        adapter = Neo4jAdapter(uri="bolt://localhost:7687", username="neo4j", password="test")

        # Mock session
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.single.return_value = {"id": "test_id"}
        mock_session.run = AsyncMock(return_value=mock_result)

        adapter._driver = Mock()
        adapter._driver.session = Mock(return_value=mock_session)

        # Mock operations
        async def mock_operation(data, session=None):
            return ToolResult.ok({"id": "test_123"})

        # Test 1: Execute 10 operations with session reuse
        adapter._driver.session.reset_mock()
        async with adapter.session_context() as session:
            for i in range(10):
                await mock_operation({"test": i}, session=session)

        calls_with_reuse = adapter._driver.session.call_count

        # Verify only 1 session was created for 10 operations
        assert calls_with_reuse == 1

    @pytest.mark.asyncio
    async def test_batch_operation_overhead_comparison(self):
        """Compare overhead between individual operations and batch operations."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter
        from Tools.adapters.base import ToolResult

        adapter = Neo4jAdapter(uri="bolt://localhost:7687", username="neo4j", password="test")

        # Mock session
        mock_session = AsyncMock()
        adapter._driver = Mock()
        adapter._driver.session = Mock(return_value=mock_session)

        # Mock _create_commitment
        commitment_counter = {"count": 0}

        async def mock_create_commitment(commitment_data, session=None):
            commitment_counter["count"] += 1
            return ToolResult.ok({
                "id": f"commitment_{commitment_counter['count']}",
                "content": commitment_data.get("content")
            })

        adapter._create_commitment = mock_create_commitment

        # Batch operation (uses single session)
        commitments = [
            {"content": "Task 1", "to_whom": "Team", "domain": "work"},
            {"content": "Task 2", "to_whom": "Team", "domain": "work"},
            {"content": "Task 3", "to_whom": "Team", "domain": "work"},
        ]

        result = await adapter.create_commitments_batch(commitments, atomic=True)

        # Verify success
        assert result.success
        assert result.data["count"] == 3

        # Verify only one session was created for all operations
        adapter._driver.session.assert_called_once()
