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
