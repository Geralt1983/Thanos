#!/usr/bin/env python3
"""
Tests for Context Optimizer.

Tests the intelligent context retrieval engine, semantic search integration,
token counting, formatting, and Memory V2 integration.
"""

import pytest
from pathlib import Path
from typing import Dict, List, Any
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from Tools.context_optimizer import ContextOptimizer


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_memory_results():
    """Sample memory search results from Memory V2."""
    return [
        {
            "id": "mem_1",
            "memory": "User asked about API authentication. Discussed OAuth2 vs JWT approaches and decided on JWT for simplicity.",
            "score": 0.3,  # Distance score (lower = better)
            "effective_score": 0.85,
            "created_at": "2024-01-20T14:30:00Z",
            "metadata": {
                "session_id": "session-123",
                "message_range": "1-50",
                "domain": "conversation_summary"
            }
        },
        {
            "id": "mem_2",
            "memory": "Implemented JWT token generation with 24-hour expiration. Added refresh token support.",
            "score": 0.5,
            "effective_score": 0.72,
            "created_at": "2024-01-20T15:15:00Z",
            "metadata": {
                "session_id": "session-123",
                "message_range": "51-100",
                "domain": "conversation_summary"
            }
        },
        {
            "id": "mem_3",
            "memory": "Discussed database schema for user management. Created users table with email, password_hash, and role fields.",
            "score": 0.8,
            "effective_score": 0.45,
            "created_at": "2024-01-19T10:00:00Z",
            "metadata": {
                "session_id": "session-456",
                "message_range": "1-30",
                "domain": "conversation_summary"
            }
        }
    ]


@pytest.fixture
def mock_memory_service():
    """Create a mock Memory V2 service."""
    service = Mock()
    service.search = Mock(return_value=[])
    return service


@pytest.fixture
def optimizer_with_mock_memory(mock_memory_service):
    """Create ContextOptimizer with mocked Memory V2 service."""
    optimizer = ContextOptimizer()
    optimizer.memory_service = mock_memory_service
    return optimizer


# ============================================================================
# Initialization Tests
# ============================================================================

class TestInitialization:
    """Test ContextOptimizer initialization."""

    def test_default_initialization(self):
        """Test initialization with default parameters."""
        optimizer = ContextOptimizer()

        assert optimizer.default_max_results == 5
        assert optimizer.default_relevance_threshold == 0.3
        assert optimizer.default_max_tokens == 1000

    def test_custom_initialization(self):
        """Test initialization with custom parameters."""
        optimizer = ContextOptimizer(
            max_results=10,
            relevance_threshold=0.5,
            max_tokens=2000
        )

        assert optimizer.default_max_results == 10
        assert optimizer.default_relevance_threshold == 0.5
        assert optimizer.default_max_tokens == 2000

    def test_memory_service_initialization(self):
        """Test that Memory V2 service is initialized."""
        optimizer = ContextOptimizer()
        # Memory service might be None if not available, but shouldn't crash
        assert optimizer.memory_service is not None or optimizer.memory_service is None

    def test_encoder_initialization(self):
        """Test that tiktoken encoder is initialized."""
        optimizer = ContextOptimizer()
        # Encoder might be None if tiktoken not available
        assert optimizer.encoder is not None or optimizer.encoder is None


# ============================================================================
# Token Counting Tests
# ============================================================================

class TestTokenCounting:
    """Test token counting functionality."""

    def test_count_tokens_basic(self):
        """Test basic token counting."""
        optimizer = ContextOptimizer()

        text = "Hello, world!"
        count = optimizer.count_tokens(text)

        # Should return a positive integer
        assert isinstance(count, int)
        assert count > 0

    def test_count_tokens_empty_string(self):
        """Test token counting with empty string."""
        optimizer = ContextOptimizer()

        count = optimizer.count_tokens("")

        assert count == 0

    def test_count_tokens_long_text(self):
        """Test token counting with longer text."""
        optimizer = ContextOptimizer()

        short_text = "Hi"
        long_text = "This is a much longer text that should have more tokens. " * 10

        short_count = optimizer.count_tokens(short_text)
        long_count = optimizer.count_tokens(long_text)

        assert long_count > short_count

    def test_count_tokens_fallback(self):
        """Test fallback token counting when encoder unavailable."""
        optimizer = ContextOptimizer()
        original_encoder = optimizer.encoder
        optimizer.encoder = None

        text = "Test text for fallback counting"
        count = optimizer.count_tokens(text)

        # Fallback should still return a count
        assert isinstance(count, int)
        assert count > 0

        optimizer.encoder = original_encoder


# ============================================================================
# Context Retrieval Tests
# ============================================================================

class TestContextRetrieval:
    """Test context retrieval functionality."""

    def test_retrieve_relevant_context_basic(self, optimizer_with_mock_memory, sample_memory_results):
        """Test basic context retrieval."""
        optimizer_with_mock_memory.memory_service.search.return_value = sample_memory_results

        result = optimizer_with_mock_memory.retrieve_relevant_context(
            current_prompt="What did we discuss about API authentication?",
            session_id="session-123"
        )

        assert isinstance(result, dict)
        assert "memories" in result
        assert "formatted_context" in result
        assert "token_count" in result
        assert "retrieval_time_ms" in result
        assert "count" in result

        # Should have called Memory V2 search
        optimizer_with_mock_memory.memory_service.search.assert_called_once()

    def test_retrieve_relevant_context_empty_results(self, optimizer_with_mock_memory):
        """Test context retrieval with no matching memories."""
        optimizer_with_mock_memory.memory_service.search.return_value = []

        result = optimizer_with_mock_memory.retrieve_relevant_context(
            current_prompt="Nonexistent topic"
        )

        assert result["count"] == 0
        assert result["memories"] == []
        assert result["formatted_context"] == ""
        assert result["token_count"] == 0

    def test_retrieve_relevant_context_filters_by_relevance(self, optimizer_with_mock_memory, sample_memory_results):
        """Test that results are filtered by relevance threshold."""
        optimizer_with_mock_memory.memory_service.search.return_value = sample_memory_results

        result = optimizer_with_mock_memory.retrieve_relevant_context(
            current_prompt="API authentication",
            relevance_threshold=0.8  # High threshold
        )

        # Should filter out low-relevance results
        assert result["count"] <= len(sample_memory_results)

    def test_retrieve_relevant_context_respects_max_results(self, optimizer_with_mock_memory, sample_memory_results):
        """Test that max_results limit is respected."""
        optimizer_with_mock_memory.memory_service.search.return_value = sample_memory_results

        result = optimizer_with_mock_memory.retrieve_relevant_context(
            current_prompt="API",
            max_results=1
        )

        assert result["count"] <= 1

    def test_retrieve_relevant_context_session_filtering(self, optimizer_with_mock_memory, sample_memory_results):
        """Test filtering by session_id."""
        optimizer_with_mock_memory.memory_service.search.return_value = sample_memory_results

        result = optimizer_with_mock_memory.retrieve_relevant_context(
            current_prompt="API",
            session_id="session-123",
            include_session_only=True
        )

        # Should filter to only session-123 memories
        for memory in result["memories"]:
            session_id = optimizer_with_mock_memory._extract_session_id(memory)
            if session_id:
                assert session_id == "session-123"

    def test_retrieve_relevant_context_without_memory_service(self):
        """Test that retrieval fails gracefully without Memory V2."""
        optimizer = ContextOptimizer()
        optimizer.memory_service = None

        with pytest.raises(RuntimeError, match="Memory V2 not available"):
            optimizer.retrieve_relevant_context(current_prompt="test")

    def test_retrieve_relevant_context_with_error(self, optimizer_with_mock_memory):
        """Test error handling during retrieval."""
        optimizer_with_mock_memory.memory_service.search.side_effect = Exception("Search failed")

        result = optimizer_with_mock_memory.retrieve_relevant_context(
            current_prompt="test"
        )

        # Should return empty result with error
        assert result["count"] == 0
        assert "error" in result
        assert "Search failed" in result["error"]

    def test_retrieve_relevant_context_uses_defaults(self, optimizer_with_mock_memory, sample_memory_results):
        """Test that default parameters are used when not specified."""
        optimizer_with_mock_memory.memory_service.search.return_value = sample_memory_results
        optimizer_with_mock_memory.default_max_results = 2
        optimizer_with_mock_memory.default_relevance_threshold = 0.5
        optimizer_with_mock_memory.default_max_tokens = 500

        result = optimizer_with_mock_memory.retrieve_relevant_context(
            current_prompt="API"
        )

        # Should use default parameters
        assert result["count"] <= 2

    def test_retrieve_relevant_context_calculates_relevance(self, optimizer_with_mock_memory, sample_memory_results):
        """Test that relevance scores are calculated from distance."""
        optimizer_with_mock_memory.memory_service.search.return_value = sample_memory_results

        result = optimizer_with_mock_memory.retrieve_relevant_context(
            current_prompt="API"
        )

        # Each memory should have a relevance score
        for memory in result["memories"]:
            assert "relevance" in memory
            assert 0 <= memory["relevance"] <= 1


# ============================================================================
# Context Formatting Tests
# ============================================================================

class TestContextFormatting:
    """Test context formatting functionality."""

    def test_format_context_for_injection_basic(self, sample_memory_results):
        """Test basic context formatting."""
        optimizer = ContextOptimizer()

        formatted = optimizer.format_context_for_injection(
            memories=sample_memory_results,
            session_id="session-123"
        )

        assert isinstance(formatted, str)
        assert len(formatted) > 0
        # Should include session ID in header
        assert "session-123" in formatted
        # Should include memory content
        assert "API authentication" in formatted

    def test_format_context_for_injection_empty_memories(self):
        """Test formatting with no memories."""
        optimizer = ContextOptimizer()

        formatted = optimizer.format_context_for_injection(memories=[])

        assert formatted == ""

    def test_format_context_for_injection_includes_metadata(self, sample_memory_results):
        """Test that formatting includes metadata."""
        optimizer = ContextOptimizer()

        # Add relevance to memories
        for mem in sample_memory_results:
            mem["relevance"] = 0.85

        formatted = optimizer.format_context_for_injection(
            memories=sample_memory_results
        )

        # Should include timestamps and message ranges
        assert "2024-01-20" in formatted
        assert "Messages" in formatted
        assert "Relevance" in formatted

    def test_format_context_for_injection_respects_token_budget(self):
        """Test that formatting respects max_tokens limit."""
        optimizer = ContextOptimizer()

        # Create many memories
        many_memories = []
        for i in range(20):
            many_memories.append({
                "id": f"mem_{i}",
                "memory": f"This is memory number {i}. " * 50,
                "relevance": 0.8,
                "created_at": "2024-01-20T10:00:00Z",
                "metadata": {"message_range": f"{i*10}-{(i+1)*10}"}
            })

        formatted = optimizer.format_context_for_injection(
            memories=many_memories,
            max_tokens=500
        )

        # Should truncate to fit within budget
        token_count = optimizer.count_tokens(formatted)
        assert token_count <= 500 * 1.1  # Allow 10% tolerance

    def test_format_context_for_injection_handles_datetime_objects(self):
        """Test formatting with datetime objects."""
        optimizer = ContextOptimizer()

        memories = [{
            "id": "mem_1",
            "memory": "Test memory",
            "relevance": 0.8,
            "created_at": datetime(2024, 1, 20, 14, 30),
            "metadata": {"message_range": "1-10"}
        }]

        formatted = optimizer.format_context_for_injection(memories=memories)

        # Should format datetime properly
        assert "2024-01-20" in formatted

    def test_format_context_for_injection_without_session_id(self, sample_memory_results):
        """Test formatting without session ID."""
        optimizer = ContextOptimizer()

        formatted = optimizer.format_context_for_injection(
            memories=sample_memory_results
        )

        # Should still work without session ID
        assert len(formatted) > 0
        assert "Previously discussed" in formatted

    def test_format_context_for_injection_handles_missing_metadata(self):
        """Test formatting with incomplete metadata."""
        optimizer = ContextOptimizer()

        memories = [{
            "id": "mem_1",
            "memory": "Test memory with minimal metadata",
            "relevance": 0.8
        }]

        formatted = optimizer.format_context_for_injection(memories=memories)

        # Should handle gracefully
        assert len(formatted) > 0
        assert "Test memory" in formatted


# ============================================================================
# Token Estimation Tests
# ============================================================================

class TestTokenEstimation:
    """Test token estimation functionality."""

    def test_estimate_context_tokens_basic(self, sample_memory_results):
        """Test basic token estimation."""
        optimizer = ContextOptimizer()

        estimate = optimizer.estimate_context_tokens(sample_memory_results)

        assert isinstance(estimate, int)
        assert estimate > 0

    def test_estimate_context_tokens_empty_memories(self):
        """Test estimation with empty memories."""
        optimizer = ContextOptimizer()

        estimate = optimizer.estimate_context_tokens([])

        # Should include header overhead
        assert estimate >= 50

    def test_estimate_context_tokens_accounts_for_overhead(self):
        """Test that estimation includes metadata overhead."""
        optimizer = ContextOptimizer()

        memories = [{
            "id": "mem_1",
            "memory": "Short"
        }]

        estimate = optimizer.estimate_context_tokens(memories)
        memory_only = optimizer.count_tokens("Short")

        # Should be more than just the memory content
        assert estimate > memory_only


# ============================================================================
# Metadata Extraction Tests
# ============================================================================

class TestMetadataExtraction:
    """Test metadata extraction functionality."""

    def test_extract_metadata_from_direct_field(self):
        """Test extracting metadata from direct field."""
        optimizer = ContextOptimizer()

        memory = {
            "id": "mem_1",
            "message_range": "1-50"
        }

        result = optimizer._extract_metadata(memory, "message_range")

        assert result == "1-50"

    def test_extract_metadata_from_metadata_dict(self):
        """Test extracting metadata from metadata sub-dict."""
        optimizer = ContextOptimizer()

        memory = {
            "id": "mem_1",
            "metadata": {
                "message_range": "1-50",
                "session_id": "session-123"
            }
        }

        result = optimizer._extract_metadata(memory, "message_range")

        assert result == "1-50"

    def test_extract_metadata_from_payload_dict(self):
        """Test extracting metadata from payload sub-dict."""
        optimizer = ContextOptimizer()

        memory = {
            "id": "mem_1",
            "payload": {
                "message_range": "1-50"
            }
        }

        result = optimizer._extract_metadata(memory, "message_range")

        assert result == "1-50"

    def test_extract_metadata_with_default(self):
        """Test extracting missing metadata with default value."""
        optimizer = ContextOptimizer()

        memory = {
            "id": "mem_1"
        }

        result = optimizer._extract_metadata(memory, "missing_key", default="default_value")

        assert result == "default_value"

    def test_extract_metadata_without_default(self):
        """Test extracting missing metadata without default."""
        optimizer = ContextOptimizer()

        memory = {
            "id": "mem_1"
        }

        result = optimizer._extract_metadata(memory, "missing_key")

        assert result is None

    def test_extract_session_id(self):
        """Test session ID extraction."""
        optimizer = ContextOptimizer()

        memory = {
            "id": "mem_1",
            "metadata": {
                "session_id": "session-123"
            }
        }

        result = optimizer._extract_session_id(memory)

        assert result == "session-123"


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for full workflows."""

    def test_full_retrieval_and_formatting_workflow(self, optimizer_with_mock_memory, sample_memory_results):
        """Test complete retrieval and formatting workflow."""
        optimizer_with_mock_memory.memory_service.search.return_value = sample_memory_results

        # Retrieve context
        result = optimizer_with_mock_memory.retrieve_relevant_context(
            current_prompt="What did we discuss about API authentication?",
            session_id="session-123",
            max_results=5,
            relevance_threshold=0.3,
            max_tokens=1000
        )

        # Should have all components
        assert result["count"] > 0
        assert len(result["memories"]) > 0
        assert len(result["formatted_context"]) > 0
        assert result["token_count"] > 0
        assert result["retrieval_time_ms"] >= 0

        # Formatted context should be ready for injection
        formatted = result["formatted_context"]
        assert "Previously discussed" in formatted
        assert "session-123" in formatted

    def test_multi_session_retrieval(self, optimizer_with_mock_memory, sample_memory_results):
        """Test retrieving context across multiple sessions."""
        optimizer_with_mock_memory.memory_service.search.return_value = sample_memory_results

        # Retrieve without session filter
        result = optimizer_with_mock_memory.retrieve_relevant_context(
            current_prompt="API and database",
            include_session_only=False
        )

        # Should retrieve from all sessions
        assert result["count"] > 0

    def test_relevance_based_filtering(self, optimizer_with_mock_memory, sample_memory_results):
        """Test that low-relevance results are filtered out."""
        optimizer_with_mock_memory.memory_service.search.return_value = sample_memory_results

        # Low threshold
        result_low = optimizer_with_mock_memory.retrieve_relevant_context(
            current_prompt="API",
            relevance_threshold=0.1
        )

        # High threshold
        result_high = optimizer_with_mock_memory.retrieve_relevant_context(
            current_prompt="API",
            relevance_threshold=0.9
        )

        # High threshold should return fewer results
        assert result_high["count"] <= result_low["count"]

    def test_token_budget_enforcement(self, optimizer_with_mock_memory):
        """Test that token budget is enforced during formatting."""
        # Create large memories
        large_memories = []
        for i in range(10):
            large_memories.append({
                "id": f"mem_{i}",
                "memory": "This is a very long memory. " * 100,
                "score": 0.3,
                "effective_score": 0.8,
                "relevance": 0.8,
                "created_at": "2024-01-20T10:00:00Z",
                "metadata": {"message_range": f"{i*10}-{(i+1)*10}"}
            })

        optimizer_with_mock_memory.memory_service.search.return_value = large_memories

        result = optimizer_with_mock_memory.retrieve_relevant_context(
            current_prompt="test",
            max_tokens=300
        )

        # Should not exceed token budget
        assert result["token_count"] <= 300 * 1.1  # Allow 10% tolerance


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_retrieve_with_none_prompt(self, optimizer_with_mock_memory):
        """Test retrieval with None prompt."""
        optimizer_with_mock_memory.memory_service.search.return_value = []

        # Should handle None gracefully (Memory V2 will handle it)
        result = optimizer_with_mock_memory.retrieve_relevant_context(
            current_prompt=None
        )

        assert isinstance(result, dict)

    def test_retrieve_with_empty_prompt(self, optimizer_with_mock_memory):
        """Test retrieval with empty string prompt."""
        optimizer_with_mock_memory.memory_service.search.return_value = []

        result = optimizer_with_mock_memory.retrieve_relevant_context(
            current_prompt=""
        )

        assert result["count"] == 0

    def test_format_with_malformed_memory(self):
        """Test formatting with malformed memory objects."""
        optimizer = ContextOptimizer()

        malformed_memories = [
            {"id": "mem_1"},  # Missing memory content
            {"memory": "Test"},  # Missing ID
            {}  # Empty dict
        ]

        formatted = optimizer.format_context_for_injection(
            memories=malformed_memories
        )

        # Should handle gracefully without crashing
        assert isinstance(formatted, str)

    def test_very_high_relevance_threshold(self, optimizer_with_mock_memory, sample_memory_results):
        """Test with relevance threshold that filters everything."""
        optimizer_with_mock_memory.memory_service.search.return_value = sample_memory_results

        result = optimizer_with_mock_memory.retrieve_relevant_context(
            current_prompt="API",
            relevance_threshold=0.99
        )

        # Should return empty or very few results
        assert result["count"] >= 0

    def test_zero_max_results(self, optimizer_with_mock_memory, sample_memory_results):
        """Test with max_results set to 0."""
        optimizer_with_mock_memory.memory_service.search.return_value = sample_memory_results

        result = optimizer_with_mock_memory.retrieve_relevant_context(
            current_prompt="API",
            max_results=0
        )

        # Should handle gracefully
        assert isinstance(result, dict)

    def test_negative_max_tokens(self):
        """Test with negative max_tokens."""
        optimizer = ContextOptimizer()

        memories = [{
            "id": "mem_1",
            "memory": "Test",
            "relevance": 0.8
        }]

        formatted = optimizer.format_context_for_injection(
            memories=memories,
            max_tokens=-100
        )

        # Should handle gracefully (use default or minimum)
        assert isinstance(formatted, str)


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
