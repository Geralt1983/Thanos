"""
Comprehensive edge case tests for Neo4j adapter.

Tests edge cases for all refactored methods including:
- Empty filters (empty dict, no filters)
- Null values (None in optional parameters)
- Empty strings vs None
- Zero values for integers
- Boundary conditions (min/max values)
- Special character handling in parameterized values
- Mixed edge cases

This complements the security injection prevention tests by focusing on
legitimate but edge-case inputs that might expose bugs or unexpected behavior.
"""

import pytest
from unittest.mock import AsyncMock, Mock, MagicMock
import sys


# Mock neo4j before importing the adapter
mock_neo4j = MagicMock()
sys.modules['neo4j'] = mock_neo4j


class TestGetCommitmentsEdgeCases:
    """Test edge cases for _get_commitments method."""

    @pytest.mark.asyncio
    async def test_get_commitments_no_filters(self):
        """Test _get_commitments with no filters (empty args dict)."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        # Empty args dict - should use default limit
        args = {}
        result = await adapter._get_commitments(args)

        assert result.success is True
        assert mock_session.run.called

        # Verify query was called with default limit
        call_args = mock_session.run.call_args
        assert call_args[0][1]["limit"] == 20  # Default limit

    @pytest.mark.asyncio
    async def test_get_commitments_empty_string_filters(self):
        """Test _get_commitments with empty string filters."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        # Empty strings - should be treated as falsy and not add WHERE conditions
        args = {
            'status': '',
            'domain': '',
            'to_whom': '',
            'limit': 10
        }
        result = await adapter._get_commitments(args)

        assert result.success is True

        # Verify query doesn't include WHERE clause (empty strings are falsy)
        call_args = mock_session.run.call_args
        query = call_args[0][0]
        assert "WHERE" not in query, "Empty string filters should not add WHERE clause"

    @pytest.mark.asyncio
    async def test_get_commitments_none_filters(self):
        """Test _get_commitments with None filters."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        # Explicit None values - should be treated as falsy
        args = {
            'status': None,
            'domain': None,
            'to_whom': None,
            'limit': 10
        }
        result = await adapter._get_commitments(args)

        assert result.success is True

        # Verify query doesn't include WHERE clause (None is falsy)
        call_args = mock_session.run.call_args
        query = call_args[0][0]
        assert "WHERE" not in query, "None filters should not add WHERE clause"

    @pytest.mark.asyncio
    async def test_get_commitments_zero_limit(self):
        """Test _get_commitments with zero limit."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        # Zero limit - Neo4j should handle this (returns no results)
        args = {'limit': 0}
        result = await adapter._get_commitments(args)

        assert result.success is True

        # Verify limit parameter is 0
        call_args = mock_session.run.call_args
        assert call_args[0][1]["limit"] == 0

    @pytest.mark.asyncio
    async def test_get_commitments_very_large_limit(self):
        """Test _get_commitments with very large limit."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        # Very large limit - should be accepted (Neo4j handles max results)
        args = {'limit': 1_000_000}
        result = await adapter._get_commitments(args)

        assert result.success is True

        # Verify large limit is passed through
        call_args = mock_session.run.call_args
        assert call_args[0][1]["limit"] == 1_000_000

    @pytest.mark.asyncio
    async def test_get_commitments_special_chars_in_parameterized_values(self):
        """Test _get_commitments with special characters in filter values."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        # Special characters that should be safely parameterized
        special_values = [
            "status with spaces",
            "status-with-dashes",
            "status_with_underscores",
            "status.with.dots",
            "status/with/slashes",
            "status:with:colons",
            "status@with@at",
            "status#with#hash",
            "status&with&ampersand",
            "status=with=equals",
            "status+with+plus",
            "status|with|pipe",
            "status~with~tilde",
            "status(with)parens",
            "status[with]brackets",
            "status{with}braces",
            "status<with>angles",
            "status'with'quotes",
            'status"with"doublequotes',
            "status`with`backticks",
            "status\\with\\backslashes",
            "status\nwith\nnewlines",
            "status\twith\ttabs",
            "status with émojis 🎉🚀",
            "status with 中文字符",
            "status\x00with\x00nulls",
        ]

        for special_value in special_values:
            args = {
                'status': special_value,
                'limit': 10
            }
            result = await adapter._get_commitments(args)

            # Should succeed and safely parameterize the special value
            assert result.success is True, f"Should handle special value: {repr(special_value)}"

            # Verify the value was parameterized (not interpolated into query string)
            call_args = mock_session.run.call_args
            params = call_args[0][1]
            assert params["status"] == special_value, "Special value should be parameterized as-is"

    @pytest.mark.asyncio
    async def test_get_commitments_mixed_edge_cases(self):
        """Test _get_commitments with mixed edge case conditions."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        # Mix of valid, None, and empty string filters
        args = {
            'status': 'active',  # Valid
            'domain': '',  # Empty string (falsy)
            'to_whom': None,  # None (falsy)
            'limit': 1  # Minimum valid limit
        }
        result = await adapter._get_commitments(args)

        assert result.success is True

        # Verify only the valid filter is in WHERE clause
        call_args = mock_session.run.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert "WHERE" in query, "Should have WHERE clause for status"
        assert "c.status = $status" in query
        assert params["status"] == 'active'
        assert "domain" not in params, "Empty string should not be parameterized"
        assert "to_whom" not in params, "None should not be parameterized"


class TestGetDecisionsEdgeCases:
    """Test edge cases for _get_decisions method."""

    @pytest.mark.asyncio
    async def test_get_decisions_no_filters(self):
        """Test _get_decisions with no filters."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        args = {}
        result = await adapter._get_decisions(args)

        assert result.success is True
        assert mock_session.run.called

        # Verify default limit is used
        call_args = mock_session.run.call_args
        assert call_args[0][1]["limit"] == 20

    @pytest.mark.asyncio
    async def test_get_decisions_zero_days(self):
        """Test _get_decisions with zero days filter."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        # Zero days is falsy but valid - it should NOT add a WHERE clause
        # because args.get("days") returns 0 which is falsy
        args = {'days': 0, 'limit': 10}
        result = await adapter._get_decisions(args)

        assert result.success is True

        # Verify days filter is NOT added (0 is falsy)
        call_args = mock_session.run.call_args
        query = call_args[0][0]
        # 0 is falsy, so the condition won't be added
        assert "duration" not in query or "days" not in call_args[0][1]

    @pytest.mark.asyncio
    async def test_get_decisions_negative_days(self):
        """Test _get_decisions with negative days filter."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=mock_result)
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        # Negative days - Neo4j will handle this (might return no results or all results)
        args = {'days': -7, 'limit': 10}
        result = await adapter._get_decisions(args)

        # Should succeed and pass the negative value to Neo4j
        assert result.success is True

        # Verify negative days is passed to query
        call_args = mock_session.run.call_args
        params = call_args[0][1]
        assert params.get("days") == -7

    @pytest.mark.asyncio
    async def test_get_decisions_very_large_days(self):
        """Test _get_decisions with very large days filter."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        # Very large days value
        args = {'days': 365_000, 'limit': 10}
        result = await adapter._get_decisions(args)

        assert result.success is True

        # Verify large days value is passed through
        call_args = mock_session.run.call_args
        params = call_args[0][1]
        assert params.get("days") == 365_000

    @pytest.mark.asyncio
    async def test_get_decisions_empty_domain(self):
        """Test _get_decisions with empty domain string."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        args = {'domain': '', 'limit': 10}
        result = await adapter._get_decisions(args)

        assert result.success is True

        # Empty string is falsy, should not add domain filter
        call_args = mock_session.run.call_args
        query = call_args[0][0]
        assert "d.domain" not in query


class TestGetPatternsEdgeCases:
    """Test edge cases for _get_patterns method."""

    @pytest.mark.asyncio
    async def test_get_patterns_no_filters(self):
        """Test _get_patterns with no filters."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        args = {}
        result = await adapter._get_patterns(args)

        assert result.success is True

        # Verify no WHERE clause and default limit
        call_args = mock_session.run.call_args
        query = call_args[0][0]
        assert "WHERE" not in query
        assert call_args[0][1]["limit"] == 20

    @pytest.mark.asyncio
    async def test_get_patterns_empty_type(self):
        """Test _get_patterns with empty type string."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        args = {'type': '', 'limit': 10}
        result = await adapter._get_patterns(args)

        assert result.success is True

        # Empty string is falsy, should not add type filter
        call_args = mock_session.run.call_args
        query = call_args[0][0]
        assert "p.type" not in query

    @pytest.mark.asyncio
    async def test_get_patterns_special_characters_in_type(self):
        """Test _get_patterns with special characters in type filter."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        # Type values with special characters should be safely parameterized
        special_types = [
            "behavioral-pattern",
            "type_with_underscores",
            "type.with.dots",
            "type/with/slashes",
            "type with spaces",
            "type'with'quotes",
            "type:with:colons",
        ]

        for special_type in special_types:
            args = {'type': special_type, 'limit': 10}
            result = await adapter._get_patterns(args)

            assert result.success is True, f"Should handle special type: {special_type}"

            # Verify parameterization
            call_args = mock_session.run.call_args
            params = call_args[0][1]
            assert params["type"] == special_type

    @pytest.mark.asyncio
    async def test_get_patterns_boundary_limit_values(self):
        """Test _get_patterns with boundary limit values."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        # Test various boundary values for limit
        limit_values = [1, 100, 1000, 10000, 0]

        for limit_val in limit_values:
            args = {'limit': limit_val}
            result = await adapter._get_patterns(args)

            assert result.success is True

            # Verify limit is passed through
            call_args = mock_session.run.call_args
            assert call_args[0][1]["limit"] == limit_val


class TestFindRelatedEdgeCases:
    """Test edge cases for _find_related method."""

    @pytest.mark.asyncio
    async def test_find_related_default_depth(self):
        """Test _find_related uses default depth when not provided."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        # No depth provided - should use default (2)
        args = {'node_id': 'test_123'}
        result = await adapter._find_related(args)

        assert result.success is True

        # Verify query uses default depth 2
        call_args = mock_session.run.call_args
        query = call_args[0][0]
        assert "*1..2" in query, "Should use default depth of 2"

    @pytest.mark.asyncio
    async def test_find_related_minimum_depth(self):
        """Test _find_related with minimum depth (1)."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        args = {'node_id': 'test_123', 'depth': 1}
        result = await adapter._find_related(args)

        assert result.success is True

        # Verify query uses depth 1
        call_args = mock_session.run.call_args
        query = call_args[0][0]
        assert "*1..1" in query

    @pytest.mark.asyncio
    async def test_find_related_maximum_depth(self):
        """Test _find_related with maximum depth (10)."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        args = {'node_id': 'test_123', 'depth': 10}
        result = await adapter._find_related(args)

        assert result.success is True

        # Verify query uses depth 10
        call_args = mock_session.run.call_args
        query = call_args[0][0]
        assert "*1..10" in query

    @pytest.mark.asyncio
    async def test_find_related_no_relationship_type_filter(self):
        """Test _find_related without relationship type filter."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        # No relationship_type - should match any relationship
        args = {'node_id': 'test_123', 'depth': 2}
        result = await adapter._find_related(args)

        assert result.success is True

        # Verify query doesn't filter by relationship type
        call_args = mock_session.run.call_args
        query = call_args[0][0]
        # Should have -[r*1..2]- pattern (no relationship type specified)
        assert "-[r*1..2]-" in query

    @pytest.mark.asyncio
    async def test_find_related_empty_relationship_type(self):
        """Test _find_related with empty relationship type string."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        # Empty string for relationship_type - should be treated as not provided
        args = {'node_id': 'test_123', 'depth': 2, 'relationship_type': ''}
        result = await adapter._find_related(args)

        assert result.success is True

        # Verify query doesn't filter by relationship type (empty string is falsy)
        call_args = mock_session.run.call_args
        query = call_args[0][0]
        assert "-[r*1..2]-" in query


class TestLinkNodesEdgeCases:
    """Test edge cases for _link_nodes method."""

    @pytest.mark.asyncio
    async def test_link_nodes_empty_properties(self):
        """Test _link_nodes with empty properties dict."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={'r': Mock()})
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        # Empty properties dict
        args = {
            'from_id': 'node_1',
            'to_id': 'node_2',
            'relationship': 'LEADS_TO',
            'properties': {}
        }
        result = await adapter._link_nodes(args)

        assert result.success is True

        # Verify empty properties dict is passed to query
        call_args = mock_session.run.call_args
        params = call_args[0][1]
        assert params["props"] == {}

    @pytest.mark.asyncio
    async def test_link_nodes_no_properties(self):
        """Test _link_nodes without properties parameter."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={'r': Mock()})
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        # No properties key
        args = {
            'from_id': 'node_1',
            'to_id': 'node_2',
            'relationship': 'LEADS_TO'
        }
        result = await adapter._link_nodes(args)

        assert result.success is True

        # Verify default empty dict is used
        call_args = mock_session.run.call_args
        params = call_args[0][1]
        assert params["props"] == {}

    @pytest.mark.asyncio
    async def test_link_nodes_properties_with_special_values(self):
        """Test _link_nodes with special values in properties."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={'r': Mock()})
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        # Properties with various special values
        special_props = {
            'empty_string': '',
            'none_value': None,
            'zero_int': 0,
            'zero_float': 0.0,
            'negative': -42,
            'boolean_true': True,
            'boolean_false': False,
            'special_chars': "value with 'quotes' and \"doublequotes\"",
            'unicode': "value with émojis 🎉 and 中文",
            'newlines': "value\nwith\nnewlines",
            'tabs': "value\twith\ttabs",
        }

        args = {
            'from_id': 'node_1',
            'to_id': 'node_2',
            'relationship': 'LEADS_TO',
            'properties': special_props
        }
        result = await adapter._link_nodes(args)

        assert result.success is True

        # Verify all special properties are parameterized as-is
        call_args = mock_session.run.call_args
        params = call_args[0][1]
        assert params["props"] == special_props

    @pytest.mark.asyncio
    async def test_link_nodes_all_valid_relationship_types(self):
        """Test _link_nodes accepts all valid relationship types."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter, ValidRelationshipType

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={'r': Mock()})
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        # Test all valid relationship types from enum
        valid_types = ValidRelationshipType.get_valid_types()

        for rel_type in valid_types:
            args = {
                'from_id': 'node_1',
                'to_id': 'node_2',
                'relationship': rel_type
            }
            result = await adapter._link_nodes(args)

            assert result.success is True, f"Should accept valid relationship type: {rel_type}"


class TestNullAndUndefinedHandling:
    """Test handling of null, None, and undefined values across all methods."""

    @pytest.mark.asyncio
    async def test_all_get_methods_handle_missing_optional_params(self):
        """Test that all get methods handle missing optional parameters gracefully."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        # Test each get method with completely empty args
        methods = [
            adapter._get_commitments,
            adapter._get_decisions,
            adapter._get_patterns,
        ]

        for method in methods:
            result = await method({})
            assert result.success is True, f"Method {method.__name__} should handle empty args"

    @pytest.mark.asyncio
    async def test_explicit_none_vs_missing_parameter(self):
        """Test that explicit None values are handled same as missing parameters."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        # Test with missing parameter
        args_missing = {'limit': 10}
        result1 = await adapter._get_commitments(args_missing)
        call1 = mock_session.run.call_args

        # Test with explicit None
        args_none = {'status': None, 'limit': 10}
        result2 = await adapter._get_commitments(args_none)
        call2 = mock_session.run.call_args

        # Both should succeed
        assert result1.success is True
        assert result2.success is True

        # Both should generate identical queries (None is falsy like missing)
        assert call1[0][0] == call2[0][0], "Missing and None should generate same query"


class TestBoundaryAndLimitValues:
    """Test boundary conditions and limit values across all methods."""

    @pytest.mark.asyncio
    async def test_negative_limit_values(self):
        """Test that negative limit values are handled (passed to Neo4j)."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        # Negative limit - Neo4j will handle this (might error or return no results)
        args = {'limit': -1}
        result = await adapter._get_commitments(args)

        # Should pass the value through (Neo4j will decide how to handle)
        assert result.success is True
        call_args = mock_session.run.call_args
        assert call_args[0][1]["limit"] == -1

    @pytest.mark.asyncio
    async def test_float_limit_values(self):
        """Test that float limit values are passed through (Neo4j might handle or error)."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        # Float limit - passed through to Neo4j
        args = {'limit': 10.5}
        result = await adapter._get_commitments(args)

        assert result.success is True
        call_args = mock_session.run.call_args
        assert call_args[0][1]["limit"] == 10.5

    @pytest.mark.asyncio
    async def test_very_long_string_values(self):
        """Test that very long string values are safely parameterized."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        # Very long string (100,000 characters)
        very_long_string = "a" * 100_000

        args = {'status': very_long_string, 'limit': 10}
        result = await adapter._get_commitments(args)

        assert result.success is True

        # Verify long string is parameterized as-is
        call_args = mock_session.run.call_args
        params = call_args[0][1]
        assert params["status"] == very_long_string
        assert len(params["status"]) == 100_000


class TestWhitespaceHandling:
    """Test handling of whitespace in various parameters."""

    @pytest.mark.asyncio
    async def test_whitespace_only_strings(self):
        """Test that whitespace-only strings are handled correctly."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        # Various whitespace-only strings
        whitespace_values = [
            ' ',  # Single space
            '  ',  # Multiple spaces
            '\t',  # Tab
            '\n',  # Newline
            '\r\n',  # CRLF
            '   \t\n   ',  # Mixed whitespace
        ]

        for ws_value in whitespace_values:
            args = {'status': ws_value, 'limit': 10}
            result = await adapter._get_commitments(args)

            # Should succeed - whitespace strings are truthy in Python
            assert result.success is True

            # Verify whitespace is parameterized as-is
            call_args = mock_session.run.call_args
            params = call_args[0][1]
            assert params["status"] == ws_value

    @pytest.mark.asyncio
    async def test_leading_trailing_whitespace(self):
        """Test that leading/trailing whitespace is preserved in parameterized values."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        # Values with leading/trailing whitespace
        args = {
            'status': '  active  ',
            'domain': '\twork\n',
            'to_whom': ' client ',
            'limit': 10
        }
        result = await adapter._get_commitments(args)

        assert result.success is True

        # Verify whitespace is preserved in parameters
        call_args = mock_session.run.call_args
        params = call_args[0][1]
        assert params["status"] == '  active  '
        assert params["domain"] == '\twork\n'
        assert params["to_whom"] == ' client '
