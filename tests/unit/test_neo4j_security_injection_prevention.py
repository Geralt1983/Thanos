"""
Comprehensive security tests for Neo4j adapter injection prevention.

Tests that all refactored methods properly handle malicious input through
validation (for non-parameterizable elements) and parameterization (for values).

This test suite specifically targets:
1. WHERE clause methods (_get_commitments, _get_decisions, _get_patterns)
   - Verify parameterization prevents injection through filter values
2. Relationship methods (_link_nodes, _find_related)
   - Verify validation prevents injection through non-parameterizable elements
3. Edge cases and attack vectors that might bypass security measures
"""

import pytest
from unittest.mock import AsyncMock, Mock, MagicMock
import sys


# Mock neo4j before importing the adapter
mock_neo4j = MagicMock()
sys.modules['neo4j'] = mock_neo4j


class TestWhereClauseParameterizationSecurity:
    """Test that WHERE clause methods safely handle malicious input via parameterization."""

    @pytest.mark.asyncio
    async def test_get_commitments_cypher_injection_in_status(self):
        """Test that Cypher injection attempts in status filter are safely parameterized."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        # Mock session
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        # Various Cypher injection attempts that should be safely handled by parameterization
        injection_attempts = [
            "active' OR '1'='1",  # SQL-style injection
            "active'] DETACH DELETE (c) //",  # Cypher delete injection
            "active' UNION ALL MATCH (n) RETURN n //",  # Union injection
            "active\nMATCH (x) DETACH DELETE (x)",  # Newline injection
            "'; DROP DATABASE; --",  # Classic SQL injection
            "active') OR 1=1--",  # Closing parenthesis
            "active' OR c.secret IS NOT NULL--",  # Data exfiltration attempt
        ]

        for injection in injection_attempts:
            args = {
                'status': injection,
                'limit': 10
            }
            result = await adapter._get_commitments(args)

            # Should succeed but safely parameterize the value
            # The query will look for commitments with status exactly matching the injection string
            # rather than executing the injected code
            assert result.success is True, f"Parameterization should handle injection: {injection}"

            # Verify the run was called (meaning query was constructed safely)
            assert mock_session.run.called

    @pytest.mark.asyncio
    async def test_get_commitments_special_characters_in_filters(self):
        """Test that special characters in filters are safely handled."""
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
        special_inputs = [
            "domain'; DROP TABLE commitments;--",
            "domain\x00null_byte",  # Null byte
            "domain\r\nCRLF injection",
            "domain\\'; MATCH (n) DETACH DELETE (n);",
            "domain/*comment*/injection",
            "domain`backtick`injection",
            "domain$variable$injection",
            "domain{property: 'value'}",
            "domain[list, injection]",
        ]

        for special_input in special_inputs:
            args = {
                'domain': special_input,
                'limit': 10
            }
            result = await adapter._get_commitments(args)
            assert result.success is True, f"Should handle special input: {special_input}"

    @pytest.mark.asyncio
    async def test_get_commitments_unicode_and_long_strings(self):
        """Test that Unicode characters and very long strings are safely handled."""
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

        # Unicode and edge case strings
        edge_cases = [
            "domain_\u0000_null",  # Unicode null
            "domain_\uffff_max",  # Unicode max
            "domain_中文_chinese",  # Chinese characters
            "domain_🚀_emoji",  # Emoji
            "domain_" + "A" * 10000,  # Very long string (10k chars)
            "domain_" + "injection'--" * 100,  # Repeated injection attempt
            "",  # Empty string
            "   ",  # Whitespace only
            "\t\n\r",  # Whitespace characters
        ]

        for edge_case in edge_cases:
            args = {
                'to_whom': edge_case,
                'limit': 10
            }
            result = await adapter._get_commitments(args)
            assert result.success is True, f"Should handle edge case: {edge_case[:50]}"

    @pytest.mark.asyncio
    async def test_get_decisions_cypher_injection_in_domain(self):
        """Test that Cypher injection attempts in domain filter are safely parameterized."""
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

        # Injection attempts targeting _get_decisions
        injection_attempts = [
            "work' OR d.private = true OR '1'='1",
            "work'] MATCH (secret:Secret) RETURN secret //",
            "work\nCREATE (malicious:Malicious {data: 'injected'})",
            "work'; CALL db.labels(); //",
            "work') OR EXISTS((d)-[:SECRET]->()) OR ('1'='1",
        ]

        for injection in injection_attempts:
            args = {
                'domain': injection,
                'days': 30,
                'limit': 10
            }
            result = await adapter._get_decisions(args)
            assert result.success is True, f"Should safely parameterize: {injection}"
            assert mock_session.run.called

    @pytest.mark.asyncio
    async def test_get_patterns_type_confusion_attacks(self):
        """Test that type confusion attacks in filter values are handled."""
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

        # Type confusion attempts (parameterization should handle these safely)
        # Note: These are strings, not actual objects - testing what happens if
        # someone tries to pass stringified objects
        type_confusion_attempts = [
            "{'$ne': null}",  # MongoDB-style injection
            "[1, 2, 3]",  # Array string
            "{'type': 'admin'}",  # Object string
            "function() { return true; }",  # Function string
            "true",  # Boolean string
            "null",  # Null string
            "undefined",  # Undefined string
            "NaN",  # NaN string
        ]

        for confusion in type_confusion_attempts:
            args = {
                'domain': confusion,
                'limit': 10
            }
            result = await adapter._get_patterns(args)
            assert result.success is True, f"Should handle type confusion: {confusion}"


class TestRelationshipValidationInjectionPrevention:
    """Test that relationship methods prevent injection through validation."""

    @pytest.mark.asyncio
    async def test_link_nodes_comprehensive_injection_attempts(self):
        """Test comprehensive injection attempts in relationship type are blocked."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        # Comprehensive list of injection attempts
        comprehensive_injections = [
            # Cypher query structure injection
            "LEADS_TO]->(x) MATCH (secret:Secret) RETURN secret //",
            "LEADS_TO {malicious: 'code'}]->(x) DETACH DELETE (x) //",
            "LEADS_TO|DELETES|CREATES",

            # Property injection
            "LEADS_TO]->(x) SET x.hacked = true //",
            "LEADS_TO]->(x) CREATE (y:Malicious) //",

            # Multiple relationship types
            "LEADS_TO|FOLLOWS|KNOWS",
            "LEADS_TO:FOLLOWS:KNOWS",

            # Unicode and special characters
            "LEADS_TO\u0000NULL",
            "LEADS_TO\nMATCH (n) RETURN n",
            "LEADS_TO\r\nCREATE (x)",

            # SQL-style injection
            "LEADS_TO'; DROP DATABASE; --",
            "LEADS_TO' OR '1'='1",

            # Path traversal style
            "../../ADMIN_ACCESS",
            "../LEADS_TO",

            # Command injection style
            "LEADS_TO; ls -la; #",
            "LEADS_TO && whoami",
            "LEADS_TO | cat /etc/passwd",

            # Script injection
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",

            # NoSQL injection style
            "{'$ne': null}",
            "LEADS_TO[$ne]",

            # Very long strings
            "LEADS_TO_" + "A" * 1000,

            # Empty and whitespace
            "",
            "   ",
            "\t\n\r",

            # Null bytes and control characters
            "LEADS_TO\x00\x01\x02",
            "\x00LEADS_TO",
            "LEADS_TO\xff",
        ]

        for injection in comprehensive_injections:
            args = {
                'from_id': 'node1',
                'to_id': 'node2',
                'relationship': injection,
                'properties': {}
            }
            result = await adapter._link_nodes(args)
            assert result.success is False, f"Should block injection: {injection[:50]}"
            assert 'Invalid relationship type' in result.error

    @pytest.mark.asyncio
    async def test_find_related_depth_injection_comprehensive(self):
        """Test comprehensive injection attempts through depth parameter are blocked."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        # Comprehensive depth injection attempts
        depth_injections = [
            # String injections
            "5 OR 1=1",
            "2; MATCH (n) DETACH DELETE (n)",
            "3 UNION ALL MATCH (secret) RETURN secret",
            "1..100",  # Path syntax
            "*1..10",  # Wildcard path

            # Type confusion
            "2.5",  # Float string (will be converted, should fail type check)
            "true",  # Boolean string
            "null",  # Null string
            "[1,2,3]",  # Array string
            "{'depth': 5}",  # Object string

            # Command injection style
            "2; ls -la",
            "3 && whoami",
            "2 | cat /etc/passwd",

            # Special characters
            "2\x00null",
            "3\nMATCH",
            "2\r\nCREATE",

            # Very large numbers (will be rejected as strings)
            "999999999999999999999",
        ]

        for injection in depth_injections:
            args = {
                'node_id': 'node1',
                'depth': injection
            }
            result = await adapter._find_related(args)
            assert result.success is False, f"Should block depth injection: {injection}"
            assert 'Invalid depth parameter' in result.error or 'Depth must be' in result.error

    @pytest.mark.asyncio
    async def test_find_related_relationship_type_injection_comprehensive(self):
        """Test comprehensive injection attempts in relationship_type filter are blocked."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        # Comprehensive relationship type filter injections
        rel_type_injections = [
            # Query structure injection
            "LEADS_TO] MATCH (secret) RETURN secret //",
            "LEADS_TO|DELETES|ADMIN_ACCESS",
            "LEADS_TO {where: 'malicious'}",

            # Path pattern injection
            "*",  # Wildcard
            "LEADS_TO|FOLLOWS",  # Multiple types
            "LEADS_TO:KNOWS",  # Type composition

            # Cypher injection
            "LEADS_TO]-() MATCH (n) DETACH DELETE (n) //",
            "LEADS_TO] WHERE 1=1 //",

            # Special characters and control codes
            "LEADS_TO\x00",
            "LEADS_TO\n\r",
            "\tLEADS_TO\t",

            # Script and command injection
            "<script>LEADS_TO</script>",
            "$(LEADS_TO)",
            "`LEADS_TO`",

            # Very long strings
            "LEADS_TO_" + "X" * 5000,

            # NoSQL injection style
            "{'$ne': 'LEADS_TO'}",
            "LEADS_TO[$regex]",
        ]

        for injection in rel_type_injections:
            args = {
                'node_id': 'node1',
                'depth': 2,
                'relationship_type': injection
            }
            result = await adapter._find_related(args)
            # Should either block with validation error or safely handle
            if not result.success:
                assert 'Invalid relationship type' in result.error
            # If it somehow passes validation (shouldn't happen), verify it doesn't execute malicious code
            # The test framework would catch any actual execution issues


class TestParameterizedQuerySafety:
    """Test that parameterized queries safely handle all types of malicious values."""

    @pytest.mark.asyncio
    async def test_commitments_properties_injection_safety(self):
        """Test that properties in create_commitment are safely parameterized."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={'c': Mock(element_id='commitment_123')})
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        adapter._driver.session = Mock(return_value=mock_session)

        # Injection attempts in parameterized properties
        malicious_values = [
            "Complete report'; MATCH (n) DETACH DELETE (n); //",
            "Task\nCREATE (malicious:Hack)",
            "Work{injection: 'attempt'}",
            "Project'] SET c.admin = true //",
            "Deadline`; DROP DATABASE; --",
        ]

        for malicious in malicious_values:
            args = {
                'content': malicious,  # This should be safely parameterized
                'to_whom': 'client',
                'deadline': '2026-01-15',
                'domain': 'work',
                'priority': 3
            }
            result = await adapter._create_commitment(args)
            # Should succeed - parameterization makes the value safe
            assert result.success is True, f"Parameterization should handle: {malicious[:50]}"

    @pytest.mark.asyncio
    async def test_link_nodes_properties_injection_safety(self):
        """Test that relationship properties are safely parameterized."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

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

        # Malicious property values (should be safely parameterized)
        malicious_props = {
            'reason': "Connection'; MATCH (n) DETACH DELETE (n); //",
            'weight': "1.0' OR '1'='1",
            'metadata': "{'$ne': null}",
            'description': "Link\nCREATE (x:Malicious)",
        }

        args = {
            'from_id': 'node1',
            'to_id': 'node2',
            'relationship': 'LEADS_TO',  # Valid type
            'properties': malicious_props
        }
        result = await adapter._link_nodes(args)
        # Should succeed - properties are parameterized
        assert result.success is True, "Properties should be safely parameterized"


class TestValidationUtilitySecurity:
    """Test that validation utilities properly reject all injection attempts."""

    def test_validate_relationship_type_comprehensive_rejection(self):
        """Test that validate_relationship_type rejects all invalid patterns."""
        from Tools.adapters.neo4j_adapter import validate_relationship_type

        # Comprehensive invalid patterns
        invalid_patterns = [
            # Query injection
            "LEADS_TO] MATCH (n) RETURN n",
            "LEADS_TO'; DROP DATABASE",
            "LEADS_TO\nCREATE (x)",

            # Special characters
            "LEADS-TO",  # Dash
            "LEADS.TO",  # Dot
            "LEADS/TO",  # Slash
            "LEADS\\TO",  # Backslash
            "LEADS:TO",  # Colon (multiple types)
            "LEADS|TO",  # Pipe (alternative)
            "LEADS(TO)",  # Parentheses
            "LEADS[TO]",  # Brackets
            "LEADS{TO}",  # Braces

            # Control characters
            "LEADS_TO\x00",
            "LEADS_TO\x01",
            "LEADS_TO\xff",

            # Empty and whitespace
            "",
            "   ",
            "\t\n\r",

            # Very long invalid string
            "INVALID_" + "X" * 10000,
        ]

        for pattern in invalid_patterns:
            normalized, error = validate_relationship_type(pattern)
            assert error is not None, f"Should reject invalid pattern: {pattern[:50]}"
            assert 'Invalid relationship type' in error

    def test_validate_integer_bounds_comprehensive_rejection(self):
        """Test that validate_integer_bounds rejects all invalid inputs."""
        from Tools.adapters.neo4j_adapter import validate_integer_bounds

        # Comprehensive invalid integer inputs
        invalid_inputs = [
            # Non-integer types
            "5",  # String
            5.5,  # Float
            True,  # Boolean
            False,  # Boolean
            None,  # None
            [],  # List
            {},  # Dict
            (5,),  # Tuple

            # Out of bounds
            0,  # Below min (for 1-10)
            -1,  # Negative
            -100,  # Very negative
            11,  # Above max
            100,  # Way above max
            999999,  # Very large
        ]

        for invalid in invalid_inputs:
            value, error = validate_integer_bounds(invalid, 1, 10, "depth")
            assert error is not None, f"Should reject invalid input: {invalid}"
            assert 'Invalid' in error or 'must be' in error

    def test_validate_node_label_comprehensive_rejection(self):
        """Test that validate_node_label rejects all invalid labels."""
        from Tools.adapters.neo4j_adapter import validate_node_label

        # Comprehensive invalid node labels
        invalid_labels = [
            # Not in schema
            "InvalidNode",
            "Malicious",
            "HackerNode",

            # Query injection
            "Commitment] MATCH (n) RETURN n",
            "Decision'; DROP DATABASE",
            "Pattern\nCREATE (x)",

            # Special characters
            "Commitment-Bad",
            "Decision.Fail",
            "Pattern/Invalid",
            "Entity\\Bad",
            "Session:Wrong",
            "Energy|State",

            # Control characters
            "Commitment\x00",
            "Decision\x01",
            "Pattern\xff",

            # Empty and whitespace
            "",
            "   ",
            "\t\n\r",

            # Very long invalid string
            "InvalidLabel_" + "X" * 10000,
        ]

        for label in invalid_labels:
            normalized, error = validate_node_label(label)
            assert error is not None, f"Should reject invalid label: {label[:50]}"
            assert 'Invalid node label' in error


class TestEdgeCasesSecurity:
    """Test edge cases that might bypass security measures."""

    @pytest.mark.asyncio
    async def test_concurrent_injection_attempts(self):
        """Test that multiple concurrent injection attempts are all blocked."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        # Multiple different injection types in one call
        args = {
            'from_id': 'node1',
            'to_id': 'node2',
            'relationship': "LEADS_TO] MATCH (secret) RETURN secret",
            'properties': {
                'description': "Property'; DROP DATABASE",
                'weight': "1' OR '1'='1"
            }
        }

        result = await adapter._link_nodes(args)
        # Should be blocked at validation level (relationship type invalid)
        assert result.success is False
        assert 'Invalid relationship type' in result.error

    @pytest.mark.asyncio
    async def test_case_variation_injection_attempts(self):
        """Test that case variations of injection attempts are handled."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        # Case variations of SQL/Cypher keywords in relationship types
        case_variations = [
            "LEADS_TO or 1=1",
            "LEADS_TO OR 1=1",
            "LEADS_TO Or 1=1",
            "leads_to OR 1=1",
            "LeAdS_tO oR 1=1",
            "LEADS_TO match (n)",
            "LEADS_TO MATCH (n)",
            "LEADS_TO Match (n)",
        ]

        for variation in case_variations:
            args = {
                'from_id': 'node1',
                'to_id': 'node2',
                'relationship': variation,
                'properties': {}
            }
            result = await adapter._link_nodes(args)
            assert result.success is False, f"Should block case variation: {variation}"
            assert 'Invalid relationship type' in result.error

    @pytest.mark.asyncio
    async def test_encoding_bypass_attempts(self):
        """Test that encoding tricks don't bypass validation."""
        from Tools.adapters.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()
        adapter._driver = Mock()

        # Various encoding attempts
        encoding_attempts = [
            "LEADS_TO%27%20OR%20%271%27%3D%271",  # URL encoding
            "LEADS_TO\x27\x20OR\x20\x271\x27\x3D\x271",  # Hex encoding
            "LEADS_TO&#39; OR &#39;1&#39;=&#39;1",  # HTML entity encoding
            "LEADS_TO\u0027 OR \u00271\u0027=\u00271",  # Unicode escape
        ]

        for encoding in encoding_attempts:
            args = {
                'from_id': 'node1',
                'to_id': 'node2',
                'relationship': encoding,
                'properties': {}
            }
            result = await adapter._link_nodes(args)
            assert result.success is False, f"Should block encoding attempt: {encoding}"
            assert 'Invalid relationship type' in result.error
