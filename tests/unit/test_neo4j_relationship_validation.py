"""
Unit tests for Neo4j relationship type validation.

Tests the security validation of relationship types in _link_nodes method,
ensuring that only whitelisted relationship types can be used and that
injection attempts are properly blocked.
"""

import pytest
from unittest.mock import AsyncMock, Mock, MagicMock
import sys


# Mock neo4j before importing the adapter
mock_neo4j = MagicMock()
sys.modules['neo4j'] = mock_neo4j


class TestRelationshipTypeValidation:
    """Test relationship type validation against injection attacks."""

    @pytest.mark.asyncio
    async def test_valid_relationship_types_accepted(self):
        """Test that all valid relationship types from enum are accepted."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter, ValidRelationshipType

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        # Mock successful session
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={
            'a': Mock(element_id='node1'),
            'r': Mock(type='LEADS_TO', element_id='rel123'),
            'b': Mock(element_id='node2')
        })
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        # Test each valid relationship type
        valid_types = ValidRelationshipType.get_valid_types()
        for rel_type in valid_types:
            args = {
                'from_id': 'node1',
                'to_id': 'node2',
                'relationship': rel_type,
                'properties': {}
            }
            result = await adapter._link_nodes(args)
            assert result.success is True, f"Valid type {rel_type} should be accepted"

    @pytest.mark.asyncio
    async def test_invalid_relationship_type_rejected(self):
        """Test that invalid relationship types are rejected."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        # Invalid relationship types that should be rejected
        invalid_types = [
            'INVALID_TYPE',
            'MALICIOUS',
            'ARBITRARY_REL',
            'NOT_IN_SCHEMA'
        ]

        for invalid_type in invalid_types:
            args = {
                'from_id': 'node1',
                'to_id': 'node2',
                'relationship': invalid_type,
                'properties': {}
            }
            result = await adapter._link_nodes(args)
            assert result.success is False, f"Invalid type {invalid_type} should be rejected"
            assert 'Invalid relationship type' in result.error
            assert 'must be one of' in result.error

    @pytest.mark.asyncio
    async def test_case_insensitive_validation(self):
        """Test that relationship types are validated case-insensitively."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        # Mock successful session
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={
            'a': Mock(element_id='node1'),
            'r': Mock(type='LEADS_TO', element_id='rel123'),
            'b': Mock(element_id='node2')
        })
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        # Test lowercase version of valid type
        args = {
            'from_id': 'node1',
            'to_id': 'node2',
            'relationship': 'leads_to',  # lowercase
            'properties': {}
        }
        result = await adapter._link_nodes(args)
        assert result.success is True
        assert result.data['relationship'] == 'LEADS_TO'  # normalized to uppercase

    @pytest.mark.asyncio
    async def test_space_normalization(self):
        """Test that spaces in relationship names are normalized to underscores."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        # Mock successful session
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={
            'a': Mock(element_id='node1'),
            'r': Mock(type='LEARNED_FROM', element_id='rel123'),
            'b': Mock(element_id='node2')
        })
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        # Test with spaces (should be normalized to underscores)
        args = {
            'from_id': 'node1',
            'to_id': 'node2',
            'relationship': 'LEARNED FROM',  # space instead of underscore
            'properties': {}
        }
        result = await adapter._link_nodes(args)
        assert result.success is True
        assert result.data['relationship'] == 'LEARNED_FROM'

    @pytest.mark.asyncio
    async def test_injection_attempt_with_cypher_syntax(self):
        """Test that Cypher injection attempts are blocked."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        # Various injection attempts
        injection_attempts = [
            "LEADS_TO]->(x) WHERE x.secret = 'leaked",  # Query structure injection
            "LEADS_TO]; DROP DATABASE;--",              # SQL-style injection
            "LEADS_TO|IMPACTS",                         # Multiple types
            "LEADS_TO {malicious: 'code'}",             # Property injection
            "*",                                         # Wildcard
            "LEADS_TO*1..5",                            # Path expression
            "LEADS_TO UNION ALL MATCH",                 # Union injection
        ]

        for injection in injection_attempts:
            args = {
                'from_id': 'node1',
                'to_id': 'node2',
                'relationship': injection,
                'properties': {}
            }
            result = await adapter._link_nodes(args)
            assert result.success is False, f"Injection attempt '{injection}' should be blocked"
            assert 'Invalid relationship type' in result.error

    @pytest.mark.asyncio
    async def test_special_characters_rejected(self):
        """Test that relationship types with special characters are rejected."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        # Special characters that should not be in relationship types
        special_char_attempts = [
            "LEADS-TO",           # Dash
            "LEADS.TO",           # Dot
            "LEADS$TO",           # Dollar sign
            "LEADS@TO",           # At symbol
            "LEADS#TO",           # Hash
            "LEADS%TO",           # Percent
            "LEADS&TO",           # Ampersand
            "LEADS*TO",           # Asterisk
            "LEADS(TO)",          # Parentheses
            "LEADS[TO]",          # Brackets
            "LEADS{TO}",          # Braces
            "LEADS'TO",           # Single quote
            'LEADS"TO',           # Double quote
            "LEADS;TO",           # Semicolon
            "LEADS:TO",           # Colon
            "LEADS/TO",           # Slash
            "LEADS\\TO",          # Backslash
        ]

        for attempt in special_char_attempts:
            args = {
                'from_id': 'node1',
                'to_id': 'node2',
                'relationship': attempt,
                'properties': {}
            }
            result = await adapter._link_nodes(args)
            assert result.success is False, f"Special character in '{attempt}' should be rejected"
            assert 'Invalid relationship type' in result.error

    @pytest.mark.asyncio
    async def test_empty_relationship_type_rejected(self):
        """Test that empty relationship type is rejected."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        args = {
            'from_id': 'node1',
            'to_id': 'node2',
            'relationship': '',
            'properties': {}
        }
        result = await adapter._link_nodes(args)
        assert result.success is False
        assert 'Invalid relationship type' in result.error

    @pytest.mark.asyncio
    async def test_whitespace_only_rejected(self):
        """Test that whitespace-only relationship type is rejected."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        whitespace_attempts = [
            '   ',      # Spaces
            '\t',       # Tab
            '\n',       # Newline
            '\r\n',     # Windows newline
            '  \t  ',   # Mixed whitespace
        ]

        for attempt in whitespace_attempts:
            args = {
                'from_id': 'node1',
                'to_id': 'node2',
                'relationship': attempt,
                'properties': {}
            }
            result = await adapter._link_nodes(args)
            assert result.success is False, f"Whitespace '{repr(attempt)}' should be rejected"
            assert 'Invalid relationship type' in result.error

    @pytest.mark.asyncio
    async def test_error_message_includes_valid_types(self):
        """Test that error messages include list of valid types."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter, ValidRelationshipType

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        args = {
            'from_id': 'node1',
            'to_id': 'node2',
            'relationship': 'INVALID',
            'properties': {}
        }
        result = await adapter._link_nodes(args)
        assert result.success is False

        # Check that all valid types are mentioned in error
        valid_types = ValidRelationshipType.get_valid_types()
        for valid_type in valid_types:
            assert valid_type in result.error, f"Error should mention valid type {valid_type}"

    @pytest.mark.asyncio
    async def test_error_message_shows_original_input(self):
        """Test that error messages show the original user input."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        original_input = 'invalid relationship'
        args = {
            'from_id': 'node1',
            'to_id': 'node2',
            'relationship': original_input,
            'properties': {}
        }
        result = await adapter._link_nodes(args)
        assert result.success is False
        assert original_input in result.error, "Error should show original input"

    @pytest.mark.asyncio
    async def test_error_message_shows_normalized_value(self):
        """Test that error messages show the normalized value."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        args = {
            'from_id': 'node1',
            'to_id': 'node2',
            'relationship': 'invalid type',  # Will be normalized to 'INVALID_TYPE'
            'properties': {}
        }
        result = await adapter._link_nodes(args)
        assert result.success is False
        assert 'INVALID_TYPE' in result.error, "Error should show normalized value"

    @pytest.mark.asyncio
    async def test_numeric_relationship_type_rejected(self):
        """Test that numeric-only relationship types are rejected."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        numeric_attempts = [
            '123',
            '456789',
            '0',
        ]

        for attempt in numeric_attempts:
            args = {
                'from_id': 'node1',
                'to_id': 'node2',
                'relationship': attempt,
                'properties': {}
            }
            result = await adapter._link_nodes(args)
            assert result.success is False, f"Numeric type '{attempt}' should be rejected"


class TestValidRelationshipTypeEnum:
    """Test the ValidRelationshipType enum helper methods."""

    def test_is_valid_with_valid_types(self):
        """Test is_valid returns True for valid relationship types."""
        from Tools.adapters.neo4j_adapter import ValidRelationshipType

        valid_types = [
            'LEADS_TO',
            'INVOLVES',
            'LEARNED_FROM',
            'DURING',
            'IMPACTS',
            'PRECEDED_BY',
            'AT_ENERGY'
        ]

        for rel_type in valid_types:
            assert ValidRelationshipType.is_valid(rel_type) is True

    def test_is_valid_with_invalid_types(self):
        """Test is_valid returns False for invalid relationship types."""
        from Tools.adapters.neo4j_adapter import ValidRelationshipType

        invalid_types = [
            'INVALID',
            'NOT_A_TYPE',
            'RANDOM',
            '',
            'leads_to',  # lowercase should fail (enum values are uppercase)
        ]

        for rel_type in invalid_types:
            assert ValidRelationshipType.is_valid(rel_type) is False

    def test_get_valid_types_returns_all_types(self):
        """Test get_valid_types returns all enum values."""
        from Tools.adapters.neo4j_adapter import ValidRelationshipType

        valid_types = ValidRelationshipType.get_valid_types()

        # Should return a list
        assert isinstance(valid_types, list)

        # Should have 7 types
        assert len(valid_types) == 7

        # Should contain all expected types
        expected_types = {
            'LEADS_TO',
            'INVOLVES',
            'LEARNED_FROM',
            'DURING',
            'IMPACTS',
            'PRECEDED_BY',
            'AT_ENERGY'
        }
        assert set(valid_types) == expected_types

    def test_enum_members_have_correct_values(self):
        """Test that enum members have the correct string values."""
        from Tools.adapters.neo4j_adapter import ValidRelationshipType

        assert ValidRelationshipType.LEADS_TO.value == 'LEADS_TO'
        assert ValidRelationshipType.INVOLVES.value == 'INVOLVES'
        assert ValidRelationshipType.LEARNED_FROM.value == 'LEARNED_FROM'
        assert ValidRelationshipType.DURING.value == 'DURING'
        assert ValidRelationshipType.IMPACTS.value == 'IMPACTS'
        assert ValidRelationshipType.PRECEDED_BY.value == 'PRECEDED_BY'
        assert ValidRelationshipType.AT_ENERGY.value == 'AT_ENERGY'


class TestRelationshipValidationEdgeCases:
    """Test edge cases in relationship type validation."""

    @pytest.mark.asyncio
    async def test_very_long_relationship_name_rejected(self):
        """Test that extremely long relationship names are rejected."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        # Very long string that's not in whitelist
        long_name = 'A' * 1000
        args = {
            'from_id': 'node1',
            'to_id': 'node2',
            'relationship': long_name,
            'properties': {}
        }
        result = await adapter._link_nodes(args)
        assert result.success is False
        assert 'Invalid relationship type' in result.error

    @pytest.mark.asyncio
    async def test_unicode_characters_in_relationship_rejected(self):
        """Test that Unicode characters in relationship names are rejected."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        unicode_attempts = [
            'LEADS_TO🔥',          # Emoji
            'LEADS_TO™',           # Trademark symbol
            'LEADS_TO©',           # Copyright symbol
            'LÉADS_TO',            # Accented character
            'LEADS_TO中文',        # Chinese characters
            'LEADS_TO_日本語',     # Japanese characters
        ]

        for attempt in unicode_attempts:
            args = {
                'from_id': 'node1',
                'to_id': 'node2',
                'relationship': attempt,
                'properties': {}
            }
            result = await adapter._link_nodes(args)
            assert result.success is False, f"Unicode in '{attempt}' should be rejected"

    @pytest.mark.asyncio
    async def test_null_bytes_in_relationship_rejected(self):
        """Test that null bytes in relationship names are rejected."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        args = {
            'from_id': 'node1',
            'to_id': 'node2',
            'relationship': 'LEADS\x00TO',  # Null byte
            'properties': {}
        }
        result = await adapter._link_nodes(args)
        assert result.success is False
        assert 'Invalid relationship type' in result.error

    @pytest.mark.asyncio
    async def test_validation_with_session_parameter(self):
        """Test that validation works correctly when session is provided."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        # Mock session passed as parameter
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={
            'a': Mock(element_id='node1'),
            'r': Mock(type='LEADS_TO', element_id='rel123'),
            'b': Mock(element_id='node2')
        })
        mock_session.run = AsyncMock(return_value=mock_result)

        # Valid relationship should work
        args = {
            'from_id': 'node1',
            'to_id': 'node2',
            'relationship': 'LEADS_TO',
            'properties': {}
        }
        result = await adapter._link_nodes(args, session=mock_session)
        assert result.success is True

        # Invalid relationship should still fail even with session
        args['relationship'] = 'INVALID'
        result = await adapter._link_nodes(args, session=mock_session)
        assert result.success is False
        assert 'Invalid relationship type' in result.error


class TestFindRelatedDepthValidation:
    """Test depth parameter validation in _find_related method."""

    @pytest.mark.asyncio
    async def test_valid_depth_values_accepted(self):
        """Test that valid depth values (1-10) are accepted."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        # Mock successful session
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        # Test all valid depths (1-10)
        for depth in range(1, 11):
            args = {'node_id': 'node1', 'depth': depth}
            result = await adapter._find_related(args)
            assert result.success is True, f"Valid depth {depth} should be accepted"

    @pytest.mark.asyncio
    async def test_default_depth_when_not_provided(self):
        """Test that default depth of 2 is used when not provided."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        # Mock successful session
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        # Call without depth parameter
        args = {'node_id': 'node1'}
        result = await adapter._find_related(args)

        assert result.success is True
        # Verify query was called with depth 2 (default)
        call_args = mock_session.run.call_args
        query = call_args[0][0]
        assert '*1..2' in query

    @pytest.mark.asyncio
    async def test_depth_below_minimum_rejected(self):
        """Test that depth values below 1 are rejected."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        invalid_depths = [0, -1, -5, -100]

        for depth in invalid_depths:
            args = {'node_id': 'node1', 'depth': depth}
            result = await adapter._find_related(args)
            assert result.success is False, f"Depth {depth} should be rejected"
            assert 'Invalid depth parameter' in result.error
            assert 'must be between 1 and 10' in result.error

    @pytest.mark.asyncio
    async def test_depth_above_maximum_rejected(self):
        """Test that depth values above 10 are rejected."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        invalid_depths = [11, 15, 100, 1000]

        for depth in invalid_depths:
            args = {'node_id': 'node1', 'depth': depth}
            result = await adapter._find_related(args)
            assert result.success is False, f"Depth {depth} should be rejected"
            assert 'Invalid depth parameter' in result.error
            assert 'must be between 1 and 10' in result.error

    @pytest.mark.asyncio
    async def test_non_integer_depth_rejected(self):
        """Test that non-integer depth values are rejected."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        invalid_depths = [
            '5',           # String
            5.5,           # Float
            '10',          # String number
            None,          # None
            [5],           # List
            {'depth': 5},  # Dict
            True,          # Boolean (subclass of int in Python, but explicitly excluded)
            False,         # Boolean
        ]

        for depth in invalid_depths:
            args = {'node_id': 'node1', 'depth': depth}
            result = await adapter._find_related(args)
            assert result.success is False, f"Non-integer depth {depth!r} should be rejected"
            assert 'Invalid depth parameter' in result.error
            assert 'must be an integer' in result.error

    @pytest.mark.asyncio
    async def test_depth_injection_attempts_blocked(self):
        """Test that injection attempts via depth parameter are blocked."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        injection_attempts = [
            '5; DROP DATABASE;',
            '5 OR 1=1',
            '5) MATCH (n) DETACH DELETE n //',
            '5..10',
            '5]',
        ]

        for injection in injection_attempts:
            args = {'node_id': 'node1', 'depth': injection}
            result = await adapter._find_related(args)
            assert result.success is False, f"Injection attempt {injection!r} should be blocked"
            assert 'Invalid depth parameter' in result.error

    @pytest.mark.asyncio
    async def test_depth_error_message_includes_value(self):
        """Test that error messages include the invalid depth value."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        args = {'node_id': 'node1', 'depth': 100}
        result = await adapter._find_related(args)
        assert result.success is False
        assert '100' in result.error


class TestFindRelatedRelationshipTypeValidation:
    """Test relationship type validation in _find_related method."""

    @pytest.mark.asyncio
    async def test_valid_relationship_types_accepted(self):
        """Test that all valid relationship types from enum are accepted in _find_related."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter, ValidRelationshipType

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        # Mock successful session
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        # Test each valid relationship type
        valid_types = ValidRelationshipType.get_valid_types()
        for rel_type in valid_types:
            args = {
                'node_id': 'node1',
                'relationship_type': rel_type,
                'depth': 2
            }
            result = await adapter._find_related(args)
            assert result.success is True, f"Valid type {rel_type} should be accepted"

    @pytest.mark.asyncio
    async def test_relationship_type_optional(self):
        """Test that relationship_type parameter is optional."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        # Mock successful session
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        # Call without relationship_type parameter
        args = {'node_id': 'node1', 'depth': 2}
        result = await adapter._find_related(args)
        assert result.success is True

        # Verify query doesn't have relationship type filter
        call_args = mock_session.run.call_args
        query = call_args[0][0]
        # Should have pattern like -[r*1..2]- without relationship type
        assert '-[r*1..2]-' in query or '-[r*1..2]' in query

    @pytest.mark.asyncio
    async def test_invalid_relationship_type_rejected(self):
        """Test that invalid relationship types are rejected in _find_related."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        invalid_types = [
            'INVALID_TYPE',
            'MALICIOUS',
            'ARBITRARY_REL',
            'NOT_IN_SCHEMA'
        ]

        for invalid_type in invalid_types:
            args = {
                'node_id': 'node1',
                'relationship_type': invalid_type,
                'depth': 2
            }
            result = await adapter._find_related(args)
            assert result.success is False, f"Invalid type {invalid_type} should be rejected"
            assert 'Invalid relationship type' in result.error
            assert 'must be one of' in result.error

    @pytest.mark.asyncio
    async def test_relationship_type_case_insensitive(self):
        """Test that relationship type validation is case-insensitive."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        # Mock successful session
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        # Test lowercase version
        args = {
            'node_id': 'node1',
            'relationship_type': 'leads_to',  # lowercase
            'depth': 2
        }
        result = await adapter._find_related(args)
        assert result.success is True

        # Verify query has uppercase relationship type
        call_args = mock_session.run.call_args
        query = call_args[0][0]
        assert ':LEADS_TO*' in query

    @pytest.mark.asyncio
    async def test_relationship_type_space_normalization(self):
        """Test that spaces in relationship types are normalized."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        # Mock successful session
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        # Test with spaces (should be normalized)
        args = {
            'node_id': 'node1',
            'relationship_type': 'LEARNED FROM',  # space instead of underscore
            'depth': 2
        }
        result = await adapter._find_related(args)
        assert result.success is True

        # Verify query has underscored relationship type
        call_args = mock_session.run.call_args
        query = call_args[0][0]
        assert ':LEARNED_FROM*' in query

    @pytest.mark.asyncio
    async def test_relationship_type_injection_attempts_blocked(self):
        """Test that injection attempts via relationship_type are blocked."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        injection_attempts = [
            "LEADS_TO*1..100]-(x) WHERE x.secret",
            "LEADS_TO]; DROP DATABASE;--",
            "LEADS_TO|IMPACTS",
            "LEADS_TO {malicious: 'code'}",
            "*",
            "LEADS_TO UNION ALL MATCH",
        ]

        for injection in injection_attempts:
            args = {
                'node_id': 'node1',
                'relationship_type': injection,
                'depth': 2
            }
            result = await adapter._find_related(args)
            assert result.success is False, f"Injection attempt {injection!r} should be blocked"
            assert 'Invalid relationship type' in result.error

    @pytest.mark.asyncio
    async def test_empty_relationship_type_treated_as_not_provided(self):
        """Test that empty string relationship type is treated as not provided."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        # Mock successful session
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        # Empty string should be treated as falsy (not provided)
        args = {
            'node_id': 'node1',
            'relationship_type': '',
            'depth': 2
        }
        result = await adapter._find_related(args)
        # Empty string is falsy, so it should be treated as not provided
        # Query should not have relationship type filter
        assert result.success is True

    @pytest.mark.asyncio
    async def test_relationship_type_error_message_quality(self):
        """Test that error messages for invalid relationship types are helpful."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter, ValidRelationshipType

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        args = {
            'node_id': 'node1',
            'relationship_type': 'INVALID_TYPE',
            'depth': 2
        }
        result = await adapter._find_related(args)
        assert result.success is False

        # Check error message includes original input
        assert 'INVALID_TYPE' in result.error

        # Check error message includes list of valid types
        valid_types = ValidRelationshipType.get_valid_types()
        for valid_type in valid_types:
            assert valid_type in result.error


class TestFindRelatedCombinedValidation:
    """Test combined validation scenarios in _find_related."""

    @pytest.mark.asyncio
    async def test_both_depth_and_relationship_type_validated(self):
        """Test that both parameters are validated when both provided."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        # Mock successful session
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        # Valid combination should succeed
        args = {
            'node_id': 'node1',
            'relationship_type': 'LEADS_TO',
            'depth': 3
        }
        result = await adapter._find_related(args)
        assert result.success is True

        # Verify query has both filters
        call_args = mock_session.run.call_args
        query = call_args[0][0]
        assert ':LEADS_TO*1..3' in query

    @pytest.mark.asyncio
    async def test_depth_validated_first(self):
        """Test that depth validation happens before relationship type validation."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        # Invalid depth with invalid relationship type
        # Depth error should be returned first
        args = {
            'node_id': 'node1',
            'relationship_type': 'INVALID_TYPE',
            'depth': 100  # Invalid depth
        }
        result = await adapter._find_related(args)
        assert result.success is False
        assert 'Invalid depth parameter' in result.error

    @pytest.mark.asyncio
    async def test_relationship_type_validated_after_depth(self):
        """Test that relationship type is validated when depth is valid."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        # Valid depth with invalid relationship type
        args = {
            'node_id': 'node1',
            'relationship_type': 'INVALID_TYPE',
            'depth': 3  # Valid depth
        }
        result = await adapter._find_related(args)
        assert result.success is False
        assert 'Invalid relationship type' in result.error

    @pytest.mark.asyncio
    async def test_validation_with_session_parameter(self):
        """Test that validation works when session is provided."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        # Mock session passed as parameter
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])
        mock_session.run = AsyncMock(return_value=mock_result)

        # Valid parameters should work with session
        args = {
            'node_id': 'node1',
            'relationship_type': 'LEADS_TO',
            'depth': 3
        }
        result = await adapter._find_related(args, session=mock_session)
        assert result.success is True

        # Invalid depth should fail even with session
        args['depth'] = 100
        result = await adapter._find_related(args, session=mock_session)
        assert result.success is False
        assert 'Invalid depth parameter' in result.error

        # Invalid relationship type should fail even with session
        args['depth'] = 3
        args['relationship_type'] = 'INVALID'
        result = await adapter._find_related(args, session=mock_session)
        assert result.success is False
        assert 'Invalid relationship type' in result.error


# ============================================================================
# VALIDATION UTILITY FUNCTION TESTS
# ============================================================================
# Tests for the centralized validation utility functions that prevent
# Cypher injection attacks through non-parameterizable query components.
# ============================================================================


class TestValidateRelationshipTypeUtility:
    """Test the validate_relationship_type utility function."""

    def test_valid_relationship_types(self):
        """Test that all valid relationship types are accepted."""
        from Tools.adapters.neo4j_adapter import validate_relationship_type, ValidRelationshipType

        valid_types = ValidRelationshipType.get_valid_types()
        for rel_type in valid_types:
            normalized, error = validate_relationship_type(rel_type)
            assert error is None, f"Valid type {rel_type} should have no error"
            assert normalized == rel_type, f"Type {rel_type} should not be modified"

    def test_case_insensitive_validation(self):
        """Test that validation is case-insensitive."""
        from Tools.adapters.neo4j_adapter import validate_relationship_type

        # Test lowercase
        normalized, error = validate_relationship_type("leads_to")
        assert error is None
        assert normalized == "LEADS_TO"

        # Test mixed case
        normalized, error = validate_relationship_type("LeAdS_tO")
        assert error is None
        assert normalized == "LEADS_TO"

    def test_space_normalization(self):
        """Test that spaces are normalized to underscores."""
        from Tools.adapters.neo4j_adapter import validate_relationship_type

        normalized, error = validate_relationship_type("leads to")
        assert error is None
        assert normalized == "LEADS_TO"

        normalized, error = validate_relationship_type("LEADS TO")
        assert error is None
        assert normalized == "LEADS_TO"

    def test_invalid_relationship_types(self):
        """Test that invalid relationship types are rejected."""
        from Tools.adapters.neo4j_adapter import validate_relationship_type

        invalid_types = [
            "INVALID_TYPE",
            "MALICIOUS",
            "ARBITRARY_REL",
            "NOT_IN_SCHEMA",
            "DROP TABLE",
            "CREATE INDEX"
        ]

        for invalid_type in invalid_types:
            normalized, error = validate_relationship_type(invalid_type)
            assert error is not None, f"Invalid type {invalid_type} should have error"
            assert 'Invalid relationship type' in error
            assert 'must be one of' in error
            assert normalized == invalid_type, "Original input should be returned on error"

    def test_injection_attempts_blocked(self):
        """Test that Cypher injection attempts are blocked."""
        from Tools.adapters.neo4j_adapter import validate_relationship_type

        injection_attempts = [
            "LEADS_TO] DETACH DELETE (n)-[r",
            "LEADS_TO]; DROP DATABASE",
            "LEADS_TO\nCREATE (x:Malicious)",
            "LEADS_TO/*comment*/",
            "LEADS_TO` OR 1=1--"
        ]

        for injection in injection_attempts:
            normalized, error = validate_relationship_type(injection)
            assert error is not None, f"Injection attempt should be blocked: {injection}"
            assert 'Invalid relationship type' in error

    def test_empty_and_whitespace_inputs(self):
        """Test handling of empty and whitespace-only inputs."""
        from Tools.adapters.neo4j_adapter import validate_relationship_type

        # Empty string
        normalized, error = validate_relationship_type("")
        assert error is not None
        assert 'Invalid relationship type' in error

        # Whitespace only
        normalized, error = validate_relationship_type("   ")
        assert error is not None
        assert 'Invalid relationship type' in error

    def test_special_characters_rejected(self):
        """Test that relationship types with special characters are rejected."""
        from Tools.adapters.neo4j_adapter import validate_relationship_type

        special_chars = [
            "LEADS_TO;",
            "LEADS_TO'",
            "LEADS_TO\"",
            "LEADS_TO\n",
            "LEADS_TO\t",
            "LEADS-TO",  # Dash instead of underscore
            "LEADS.TO",  # Dot instead of underscore
        ]

        for special in special_chars:
            normalized, error = validate_relationship_type(special)
            assert error is not None, f"Special character should be rejected: {special}"
            assert 'Invalid relationship type' in error


class TestValidateIntegerBoundsUtility:
    """Test the validate_integer_bounds utility function."""

    def test_valid_integers_within_bounds(self):
        """Test that valid integers within bounds are accepted."""
        from Tools.adapters.neo4j_adapter import validate_integer_bounds

        # Test various valid values
        for value in [1, 5, 10]:
            result, error = validate_integer_bounds(value, 1, 10, "depth")
            assert error is None
            assert result == value

    def test_boundary_values(self):
        """Test that boundary values are handled correctly."""
        from Tools.adapters.neo4j_adapter import validate_integer_bounds

        # Test minimum boundary
        result, error = validate_integer_bounds(1, 1, 10, "depth")
        assert error is None
        assert result == 1

        # Test maximum boundary
        result, error = validate_integer_bounds(10, 1, 10, "depth")
        assert error is None
        assert result == 10

        # Test below minimum
        result, error = validate_integer_bounds(0, 1, 10, "depth")
        assert error is not None
        assert 'must be between 1 and 10' in error
        assert result is None

        # Test above maximum
        result, error = validate_integer_bounds(11, 1, 10, "depth")
        assert error is not None
        assert 'must be between 1 and 10' in error
        assert result is None

    def test_non_integer_types_rejected(self):
        """Test that non-integer types are rejected."""
        from Tools.adapters.neo4j_adapter import validate_integer_bounds

        non_integers = [
            "5",          # String
            5.5,          # Float
            None,         # None
            [5],          # List
            {"value": 5}, # Dict
            True,         # Boolean (special case in Python)
            False,        # Boolean
        ]

        for non_int in non_integers:
            result, error = validate_integer_bounds(non_int, 1, 10, "depth")
            assert error is not None, f"Non-integer {non_int} should be rejected"
            assert 'must be an integer' in error
            assert result is None

    def test_negative_values(self):
        """Test handling of negative values."""
        from Tools.adapters.neo4j_adapter import validate_integer_bounds

        # Negative value when positive is required
        result, error = validate_integer_bounds(-5, 1, 10, "depth")
        assert error is not None
        assert 'must be between 1 and 10' in error
        assert result is None

        # Negative value in range that allows negatives
        result, error = validate_integer_bounds(-5, -10, 0, "offset")
        assert error is None
        assert result == -5

    def test_zero_value(self):
        """Test handling of zero value."""
        from Tools.adapters.neo4j_adapter import validate_integer_bounds

        # Zero when not allowed
        result, error = validate_integer_bounds(0, 1, 10, "depth")
        assert error is not None
        assert 'must be between 1 and 10' in error

        # Zero when allowed
        result, error = validate_integer_bounds(0, 0, 10, "count")
        assert error is None
        assert result == 0

    def test_large_values(self):
        """Test handling of very large values."""
        from Tools.adapters.neo4j_adapter import validate_integer_bounds

        # Value far exceeding maximum
        result, error = validate_integer_bounds(1000000, 1, 10, "depth")
        assert error is not None
        assert 'must be between 1 and 10' in error
        assert result is None

    def test_custom_parameter_names(self):
        """Test that custom parameter names appear in error messages."""
        from Tools.adapters.neo4j_adapter import validate_integer_bounds

        result, error = validate_integer_bounds(100, 1, 10, "custom_param")
        assert error is not None
        assert 'custom_param' in error.lower()

        result, error = validate_integer_bounds("not_int", 1, 10, "my_value")
        assert error is not None
        assert 'my_value' in error.lower()

    def test_depth_parameter_special_message(self):
        """Test that depth parameter gets special performance message."""
        from Tools.adapters.neo4j_adapter import validate_integer_bounds

        result, error = validate_integer_bounds(15, 1, 10, "depth")
        assert error is not None
        assert 'Use smaller depths for better performance' in error

    def test_injection_attempts_through_type_confusion(self):
        """Test that injection attempts through type confusion are blocked."""
        from Tools.adapters.neo4j_adapter import validate_integer_bounds

        injection_attempts = [
            "5; DROP TABLE",
            "5 OR 1=1",
            "5/*comment*/",
            "5\n10",
            "5\t10",
        ]

        for injection in injection_attempts:
            result, error = validate_integer_bounds(injection, 1, 10, "depth")
            assert error is not None, f"Injection attempt should be blocked: {injection}"
            assert 'must be an integer' in error
            assert result is None


class TestValidateNodeLabelUtility:
    """Test the validate_node_label utility function."""

    def test_valid_node_labels(self):
        """Test that all valid node labels are accepted."""
        from Tools.adapters.neo4j_adapter import validate_node_label

        valid_labels = ["Commitment", "Decision", "Pattern", "Entity", "Session", "EnergyState"]

        for label in valid_labels:
            normalized, error = validate_node_label(label)
            assert error is None, f"Valid label {label} should have no error"
            assert normalized == label

    def test_case_normalization(self):
        """Test that labels are normalized to canonical case form."""
        from Tools.adapters.neo4j_adapter import validate_node_label

        # Lowercase
        normalized, error = validate_node_label("commitment")
        assert error is None
        assert normalized == "Commitment"

        # Uppercase
        normalized, error = validate_node_label("DECISION")
        assert error is None
        assert normalized == "Decision"

        # Mixed case - should normalize to canonical form
        normalized, error = validate_node_label("pAtTeRn")
        assert error is None
        assert normalized == "Pattern"

        # PascalCase with multiple words - should preserve canonical form
        normalized, error = validate_node_label("energystate")
        assert error is None
        assert normalized == "EnergyState"

        normalized, error = validate_node_label("ENERGYSTATE")
        assert error is None
        assert normalized == "EnergyState"

    def test_invalid_node_labels(self):
        """Test that invalid node labels are rejected."""
        from Tools.adapters.neo4j_adapter import validate_node_label

        invalid_labels = [
            "InvalidLabel",
            "Malicious",
            "NotInSchema",
            "DROP",
            "CREATE",
        ]

        for label in invalid_labels:
            normalized, error = validate_node_label(label)
            assert error is not None, f"Invalid label {label} should have error"
            assert 'Invalid node label' in error
            assert 'must be one of' in error

    def test_injection_attempts_blocked(self):
        """Test that Cypher injection attempts through labels are blocked."""
        from Tools.adapters.neo4j_adapter import validate_node_label

        injection_attempts = [
            "Commitment] DETACH DELETE (n",
            "Decision); DROP DATABASE",
            "Pattern\nCREATE (x:Malicious)",
            "Entity/*comment*/",
            "Session` OR 1=1--",
        ]

        for injection in injection_attempts:
            normalized, error = validate_node_label(injection)
            assert error is not None, f"Injection attempt should be blocked: {injection}"
            assert 'Invalid node label' in error

    def test_empty_and_whitespace_inputs(self):
        """Test handling of empty and whitespace-only inputs."""
        from Tools.adapters.neo4j_adapter import validate_node_label

        # Empty string
        normalized, error = validate_node_label("")
        assert error is not None
        assert 'Invalid node label' in error

        # Whitespace only
        normalized, error = validate_node_label("   ")
        assert error is not None
        assert 'Invalid node label' in error

    def test_special_characters_rejected(self):
        """Test that labels with special characters are rejected."""
        from Tools.adapters.neo4j_adapter import validate_node_label

        special_chars = [
            "Commitment;",
            "Decision'",
            "Pattern\"",
            "Entity\n",
            "Session\t",
            "Energy-State",  # Dash
            "Energy.State",  # Dot
        ]

        for special in special_chars:
            normalized, error = validate_node_label(special)
            assert error is not None, f"Special character should be rejected: {special}"
            assert 'Invalid node label' in error
