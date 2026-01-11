"""
Unit tests for Neo4j adapter backward compatibility.

Verifies that all adapter methods still work correctly when called WITHOUT
passing the optional session parameter, ensuring backward compatibility after
the session pooling refactor.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock, call
from datetime import datetime
import sys


# Mock neo4j before importing the adapter
mock_neo4j = MagicMock()
sys.modules['neo4j'] = mock_neo4j


class TestCommitmentOperationsBackwardCompatibility:
    """Test commitment operations work without session parameter."""

    @pytest.mark.asyncio
    async def test_create_commitment_without_session(self):
        """Test _create_commitment creates own session when none provided."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        # Create adapter with mocked driver
        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        # Mock session and result
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={
            'c': Mock(element_id='commitment_123')
        })
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        adapter._driver.session = Mock(return_value=mock_session)

        # Call without session parameter (backward compatibility)
        args = {
            'what': 'Complete the report',
            'why': 'Client deliverable',
            'by_when': '2026-01-15'
        }
        result = await adapter._create_commitment(args)

        # Verify adapter created its own session
        adapter._driver.session.assert_called_once_with(database="neo4j")

        # Verify session was used
        assert mock_session.run.called

        # Verify result is successful
        assert result.success is True
        assert 'commitment_id' in result.data

    @pytest.mark.asyncio
    async def test_complete_commitment_without_session(self):
        """Test _complete_commitment creates own session when none provided."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={
            'c': Mock(element_id='commitment_123', **{
                'what': 'Complete report',
                'completed_at': datetime.now().isoformat()
            })
        })
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        adapter._driver.session = Mock(return_value=mock_session)

        # Call without session parameter
        args = {'commitment_id': 'commitment_123', 'outcome': 'Completed successfully'}
        result = await adapter._complete_commitment(args)

        # Verify session creation
        adapter._driver.session.assert_called_once_with(database="neo4j")
        assert mock_session.run.called
        assert result.success is True

    @pytest.mark.asyncio
    async def test_get_commitments_without_session(self):
        """Test _get_commitments creates own session when none provided."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_records = [
            {'c': Mock(element_id='c1', **{'what': 'Task 1', 'status': 'pending'})},
            {'c': Mock(element_id='c2', **{'what': 'Task 2', 'status': 'pending'})}
        ]
        mock_result.data = AsyncMock(return_value=mock_records)
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        adapter._driver.session = Mock(return_value=mock_session)

        # Call without session parameter
        args = {'status': 'pending'}
        result = await adapter._get_commitments(args)

        # Verify session creation
        adapter._driver.session.assert_called_once_with(database="neo4j")
        assert mock_session.run.called
        assert result.success is True


class TestDecisionOperationsBackwardCompatibility:
    """Test decision operations work without session parameter."""

    @pytest.mark.asyncio
    async def test_record_decision_without_session(self):
        """Test _record_decision creates own session when none provided."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={
            'd': Mock(element_id='decision_123')
        })
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        adapter._driver.session = Mock(return_value=mock_session)

        # Call without session parameter
        args = {
            'what': 'Choose framework',
            'why': 'Better performance',
            'alternatives': ['React', 'Vue']
        }
        result = await adapter._record_decision(args)

        # Verify session creation
        adapter._driver.session.assert_called_once_with(database="neo4j")
        assert mock_session.run.called
        assert result.success is True
        assert 'decision_id' in result.data

    @pytest.mark.asyncio
    async def test_get_decisions_without_session(self):
        """Test _get_decisions creates own session when none provided."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_records = [
            {'d': Mock(element_id='d1', **{'what': 'Decision 1', 'category': 'technical'})},
            {'d': Mock(element_id='d2', **{'what': 'Decision 2', 'category': 'technical'})}
        ]
        mock_result.data = AsyncMock(return_value=mock_records)
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        adapter._driver.session = Mock(return_value=mock_session)

        # Call without session parameter
        args = {'category': 'technical'}
        result = await adapter._get_decisions(args)

        # Verify session creation
        adapter._driver.session.assert_called_once_with(database="neo4j")
        assert mock_session.run.called
        assert result.success is True


class TestPatternOperationsBackwardCompatibility:
    """Test pattern and session operations work without session parameter."""

    @pytest.mark.asyncio
    async def test_record_pattern_without_session(self):
        """Test _record_pattern creates own session when none provided."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()

        # Mock multiple queries for _record_pattern (check, create, link)
        mock_check_result = AsyncMock()
        mock_check_result.single = AsyncMock(return_value={'p': None})

        mock_create_result = AsyncMock()
        mock_create_result.single = AsyncMock(return_value={
            'p': Mock(element_id='pattern_123')
        })

        mock_link_result = AsyncMock()
        mock_link_result.consume = AsyncMock()

        # Mock run to return different results for different queries
        mock_session.run = AsyncMock(side_effect=[
            mock_check_result,
            mock_create_result,
            mock_link_result
        ])
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        adapter._driver.session = Mock(return_value=mock_session)

        # Call without session parameter
        args = {
            'pattern': 'morning_planning',
            'description': 'Daily planning routine',
            'context': 'productivity'
        }
        result = await adapter._record_pattern(args)

        # Verify session creation
        adapter._driver.session.assert_called_once_with(database="neo4j")

        # Verify multiple queries were executed
        assert mock_session.run.call_count == 3
        assert result.success is True

    @pytest.mark.asyncio
    async def test_get_patterns_without_session(self):
        """Test _get_patterns creates own session when none provided."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_records = [
            {'p': Mock(element_id='p1', **{'pattern': 'Pattern 1'}), 'count': 5}
        ]
        mock_result.data = AsyncMock(return_value=mock_records)
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        adapter._driver.session = Mock(return_value=mock_session)

        # Call without session parameter
        args = {}
        result = await adapter._get_patterns(args)

        # Verify session creation
        adapter._driver.session.assert_called_once_with(database="neo4j")
        assert mock_session.run.called
        assert result.success is True

    @pytest.mark.asyncio
    async def test_start_session_without_session(self):
        """Test _start_session creates own session when none provided."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={
            's': Mock(element_id='session_123')
        })
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        adapter._driver.session = Mock(return_value=mock_session)

        # Call without session parameter
        args = {'topic': 'planning', 'context': {'user': 'test'}}
        result = await adapter._start_session(args)

        # Verify session creation
        adapter._driver.session.assert_called_once_with(database="neo4j")
        assert mock_session.run.called
        assert result.success is True

    @pytest.mark.asyncio
    async def test_end_session_without_session(self):
        """Test _end_session creates own session when none provided."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={
            's': Mock(element_id='session_123', **{'ended_at': datetime.now().isoformat()})
        })
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        adapter._driver.session = Mock(return_value=mock_session)

        # Call without session parameter
        args = {'session_id': 'session_123', 'summary': 'Completed planning'}
        result = await adapter._end_session(args)

        # Verify session creation
        adapter._driver.session.assert_called_once_with(database="neo4j")
        assert mock_session.run.called
        assert result.success is True


class TestRelationshipOperationsBackwardCompatibility:
    """Test relationship operations work without session parameter."""

    @pytest.mark.asyncio
    async def test_link_nodes_without_session(self):
        """Test _link_nodes creates own session when none provided."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={
            'r': Mock(type='RELATES_TO', element_id='rel_123')
        })
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        adapter._driver.session = Mock(return_value=mock_session)

        # Call without session parameter
        args = {
            'from_id': 'node_1',
            'to_id': 'node_2',
            'relationship_type': 'RELATES_TO',
            'properties': {'strength': 0.8}
        }
        result = await adapter._link_nodes(args)

        # Verify session creation
        adapter._driver.session.assert_called_once_with(database="neo4j")
        assert mock_session.run.called
        assert result.success is True

    @pytest.mark.asyncio
    async def test_find_related_without_session(self):
        """Test _find_related creates own session when none provided."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_records = [
            {'node': Mock(element_id='n1'), 'rel': Mock(type='RELATES_TO')}
        ]
        mock_result.data = AsyncMock(return_value=mock_records)
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        adapter._driver.session = Mock(return_value=mock_session)

        # Call without session parameter
        args = {'node_id': 'node_1'}
        result = await adapter._find_related(args)

        # Verify session creation
        adapter._driver.session.assert_called_once_with(database="neo4j")
        assert mock_session.run.called
        assert result.success is True

    @pytest.mark.asyncio
    async def test_query_graph_without_session(self):
        """Test _query_graph creates own session when none provided."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_records = [{'result': 'data'}]
        mock_result.data = AsyncMock(return_value=mock_records)
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        adapter._driver.session = Mock(return_value=mock_session)

        # Call without session parameter
        args = {'query': 'MATCH (n) RETURN n LIMIT 10'}
        result = await adapter._query_graph(args)

        # Verify session creation
        adapter._driver.session.assert_called_once_with(database="neo4j")
        assert mock_session.run.called
        assert result.success is True


class TestEntityOperationsBackwardCompatibility:
    """Test entity operations work without session parameter."""

    @pytest.mark.asyncio
    async def test_create_entity_without_session(self):
        """Test _create_entity creates own session when none provided."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={
            'e': Mock(element_id='entity_123')
        })
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        adapter._driver.session = Mock(return_value=mock_session)

        # Call without session parameter
        args = {
            'type': 'Person',
            'name': 'John Doe',
            'properties': {'email': 'john@example.com'}
        }
        result = await adapter._create_entity(args)

        # Verify session creation
        adapter._driver.session.assert_called_once_with(database="neo4j")
        assert mock_session.run.called
        assert result.success is True
        assert 'entity_id' in result.data

    @pytest.mark.asyncio
    async def test_get_entity_context_without_session(self):
        """Test _get_entity_context creates own session when none provided."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_records = [
            {'entity': Mock(element_id='e1'), 'context': {'data': 'value'}}
        ]
        mock_result.data = AsyncMock(return_value=mock_records)
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        adapter._driver.session = Mock(return_value=mock_session)

        # Call without session parameter
        args = {'entity_id': 'entity_123'}
        result = await adapter._get_entity_context(args)

        # Verify session creation
        adapter._driver.session.assert_called_once_with(database="neo4j")
        assert mock_session.run.called
        assert result.success is True


class TestSessionCleanupBackwardCompatibility:
    """Test that sessions are properly cleaned up when methods create their own."""

    @pytest.mark.asyncio
    async def test_session_cleanup_on_success(self):
        """Test session is properly closed after successful operation."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={
            'c': Mock(element_id='commitment_123')
        })
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        adapter._driver.session = Mock(return_value=mock_session)

        # Execute operation
        args = {'what': 'Test', 'why': 'Testing', 'by_when': '2026-01-15'}
        await adapter._create_commitment(args)

        # Verify session context manager was properly exited
        mock_session.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_cleanup_on_error(self):
        """Test session is properly closed even when operation fails."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        # Simulate an error during query execution
        mock_session.run = AsyncMock(side_effect=Exception("Database error"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        adapter._driver.session = Mock(return_value=mock_session)

        # Execute operation (should handle error gracefully)
        args = {'what': 'Test', 'why': 'Testing', 'by_when': '2026-01-15'}

        with pytest.raises(Exception):
            await adapter._create_commitment(args)

        # Verify session context manager was properly exited even on error
        mock_session.__aexit__.assert_called_once()


class TestAllMethodsWorkIndependently:
    """Test that all methods work independently without session parameter."""

    @pytest.mark.asyncio
    async def test_all_commitment_methods_independent(self):
        """Test all commitment methods work independently."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        # Each call should create its own session
        for method_name in ['_create_commitment', '_complete_commitment', '_get_commitments']:
            mock_session = AsyncMock()
            mock_result = AsyncMock()

            if method_name == '_get_commitments':
                mock_result.data = AsyncMock(return_value=[])
            else:
                mock_result.single = AsyncMock(return_value={'c': Mock(element_id='c1')})

            mock_session.run = AsyncMock(return_value=mock_result)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)

            adapter._driver.session = Mock(return_value=mock_session)

            # Call method
            method = getattr(adapter, method_name)
            if method_name == '_create_commitment':
                await method({'what': 'Test', 'why': 'Testing', 'by_when': '2026-01-15'})
            elif method_name == '_complete_commitment':
                await method({'commitment_id': 'c1', 'outcome': 'Done'})
            else:
                await method({})

            # Verify session was created
            adapter._driver.session.assert_called()

    @pytest.mark.asyncio
    async def test_sequential_calls_create_separate_sessions(self):
        """Test that sequential calls without session param create separate sessions."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        session_count = 0

        def create_mock_session(database=None):
            nonlocal session_count
            session_count += 1
            mock_session = AsyncMock()
            mock_result = AsyncMock()
            mock_result.single = AsyncMock(return_value={
                'c': Mock(element_id=f'c{session_count}')
            })
            mock_session.run = AsyncMock(return_value=mock_result)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            return mock_session

        adapter._driver.session = Mock(side_effect=create_mock_session)

        # Make multiple calls
        args = {'what': 'Test', 'why': 'Testing', 'by_when': '2026-01-15'}
        await adapter._create_commitment(args)
        await adapter._create_commitment(args)
        await adapter._create_commitment(args)

        # Verify 3 separate sessions were created
        assert adapter._driver.session.call_count == 3
        assert session_count == 3
