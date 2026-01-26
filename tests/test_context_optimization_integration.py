#!/usr/bin/env python3
"""
Integration Tests for Context Optimization (Full Summarization Flow).

Tests the complete end-to-end flow of context window optimization:
1. Conversation history accumulation
2. Token counting and threshold detection
3. Message summarization via ConversationSummarizer
4. Summary storage in Memory V2
5. Relevant context retrieval via ContextOptimizer
6. Context injection into active conversation

Test Categories:
- TestFullSummarizationFlow: End-to-end summarization and retrieval
- TestContextWindowManagement: Token limit handling
- TestMultiSessionIntegration: Cross-session context optimization
- TestPerformanceUnderLoad: High-volume conversation handling
"""

import pytest
import json
from pathlib import Path
from typing import Dict, List, Any
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime, timedelta

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from Tools.conversation_summarizer import ConversationSummarizer, SummaryResult
from Tools.context_optimizer import ContextOptimizer


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def sample_conversation():
    """Sample conversation messages for testing."""
    messages = []

    # Opening messages about API design
    messages.extend([
        {"role": "user", "content": "I need to design a REST API for user authentication."},
        {"role": "assistant", "content": "Let's discuss the authentication approach. Are you considering OAuth2, JWT, or session-based auth?"},
        {"role": "user", "content": "I'm thinking JWT for stateless authentication."},
        {"role": "assistant", "content": "Good choice. JWT is lightweight and works well for microservices. Let's design the token structure."},
    ])

    # Middle messages about implementation
    messages.extend([
        {"role": "user", "content": "How should I handle token refresh?"},
        {"role": "assistant", "content": "Implement refresh tokens with a longer expiration. When access token expires, use refresh token to get a new one."},
        {"role": "user", "content": "What about token storage on the client?"},
        {"role": "assistant", "content": "Store access tokens in memory or sessionStorage, refresh tokens in httpOnly cookies for security."},
    ])

    # Later messages about database schema
    messages.extend([
        {"role": "user", "content": "Let's design the user database schema."},
        {"role": "assistant", "content": "We'll need a users table with id, email, password_hash, and created_at fields at minimum."},
        {"role": "user", "content": "Should I add a roles field for authorization?"},
        {"role": "assistant", "content": "Yes, add a role field. Consider using an enum or foreign key to a roles table."},
    ])

    return messages


@pytest.fixture
def long_conversation():
    """Long conversation exceeding typical context window."""
    messages = []

    # Generate 100 message pairs
    topics = [
        ("API authentication", "JWT implementation"),
        ("database schema", "user management"),
        ("error handling", "logging strategy"),
        ("deployment", "containerization"),
        ("testing", "integration tests"),
    ]

    for i in range(100):
        topic = topics[i % len(topics)]
        messages.append({
            "role": "user",
            "content": f"Question {i+1}: Can you explain more about {topic[0]}?"
        })
        messages.append({
            "role": "assistant",
            "content": f"Answer {i+1}: Let me explain {topic[1]} in detail. " + ("Here's what you need to know. " * 20)
        })

    return messages


@pytest.fixture
def mock_llm_client():
    """Create a mock LiteLLM client for ConversationSummarizer."""
    client = Mock()

    # Mock chat responses for summarization
    client.chat = Mock(side_effect=[
        # First call: summary
        "User discussed JWT authentication for REST API. Decided on JWT for stateless auth with refresh tokens stored in httpOnly cookies. Designed user database schema with roles for authorization.",
        # Second call: key points
        "- JWT chosen for stateless authentication\n- Refresh tokens with longer expiration\n- Store access tokens in memory, refresh in httpOnly cookies\n- User schema: id, email, password_hash, role, created_at",
    ])

    return client


@pytest.fixture
def mock_memory_service():
    """Create a mock Memory V2 service."""
    service = Mock()

    # Mock add method for storing summaries
    service.add = Mock(side_effect=lambda content, metadata: {
        "id": f"mem_{hash(content) % 10000}",
        "content": content,
        "metadata": metadata,
        "created_at": datetime.now().isoformat()
    })

    # Mock search method for retrieving context
    stored_summaries = []

    def mock_search(query, limit=5, filters=None):
        # Return stored summaries with relevance scores
        results = []
        for summary in stored_summaries[-limit:]:
            results.append({
                "id": summary["id"],
                "memory": summary["content"],
                "score": 0.3,  # Distance score
                "effective_score": 0.8,
                "created_at": summary["created_at"],
                "metadata": summary["metadata"]
            })
        return results

    service.search = Mock(side_effect=mock_search)
    service._stored_summaries = stored_summaries  # For test access

    return service


@pytest.fixture
def summarizer_with_mock_client(mock_llm_client):
    """ConversationSummarizer with mocked LLM client."""
    summarizer = ConversationSummarizer(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        compression_ratio=0.3
    )
    summarizer.llm_client = mock_llm_client
    return summarizer


@pytest.fixture
def optimizer_with_mock_memory(mock_memory_service):
    """ContextOptimizer with mocked Memory V2 service."""
    optimizer = ContextOptimizer(
        max_results=5,
        relevance_threshold=0.3,
        max_tokens=1000
    )
    optimizer.memory_service = mock_memory_service
    return optimizer


# =============================================================================
# Test Full Summarization Flow
# =============================================================================

class TestFullSummarizationFlow:
    """Test complete end-to-end summarization and retrieval flow."""

    def test_summarize_and_store_workflow(
        self,
        summarizer_with_mock_client,
        sample_conversation
    ):
        """Test: Summarize messages and store in Memory V2."""
        # Step 1: Count tokens in conversation
        token_count = summarizer_with_mock_client.count_message_tokens(sample_conversation)
        assert token_count > 0

        # Step 2: Estimate compression
        estimate = summarizer_with_mock_client.estimate_compression(sample_conversation)
        assert estimate["original_tokens"] == token_count
        assert estimate["estimated_summary_tokens"] < token_count
        assert estimate["savings"] > 0

        # Step 3: Generate summary
        summary = summarizer_with_mock_client.summarize_messages(
            sample_conversation,
            max_length=500
        )
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "JWT" in summary or "authentication" in summary.lower()

        # Step 4: Extract key points
        key_points = summarizer_with_mock_client.extract_key_points(sample_conversation)
        assert isinstance(key_points, list)
        assert len(key_points) > 0

        # Step 5: Store in Memory V2 (mocked)
        with patch('Tools.conversation_summarizer.MEMORY_V2_AVAILABLE', True):
            with patch('Tools.conversation_summarizer.MemoryService') as mock_service_class:
                mock_service = Mock()
                mock_service.add.return_value = {
                    "id": "mem_123",
                    "content": summary
                }
                mock_service_class.return_value = mock_service

                result = summarizer_with_mock_client.store_summary(
                    summary=summary,
                    session_id="session-test-123",
                    message_range="1-12"
                )

                assert result["id"] == "mem_123"
                mock_service.add.assert_called_once()

    def test_retrieve_and_inject_workflow(
        self,
        optimizer_with_mock_memory,
        mock_memory_service
    ):
        """Test: Retrieve stored summaries and format for injection."""
        # Simulate stored summaries in Memory V2
        mock_memory_service._stored_summaries.extend([
            {
                "id": "mem_1",
                "content": "User discussed JWT authentication. Decided on JWT with refresh tokens.",
                "metadata": {
                    "session_id": "session-123",
                    "message_range": "1-10",
                    "domain": "conversation_summary"
                },
                "created_at": datetime.now().isoformat()
            },
            {
                "id": "mem_2",
                "content": "Designed user database schema with roles for authorization.",
                "metadata": {
                    "session_id": "session-123",
                    "message_range": "11-20",
                    "domain": "conversation_summary"
                },
                "created_at": datetime.now().isoformat()
            }
        ])

        # Retrieve relevant context
        context = optimizer_with_mock_memory.retrieve_relevant_context(
            current_prompt="What did we decide about authentication?",
            session_id="session-123"
        )

        assert context["count"] > 0
        assert len(context["memories"]) > 0
        assert len(context["formatted_context"]) > 0
        assert context["token_count"] > 0
        assert context["retrieval_time_ms"] >= 0

        # Verify formatted context is ready for injection
        formatted = context["formatted_context"]
        assert "Previously discussed" in formatted or "session-123" in formatted

    def test_full_cycle_summarize_store_retrieve(
        self,
        summarizer_with_mock_client,
        optimizer_with_mock_memory,
        sample_conversation
    ):
        """Test: Complete cycle from summarization to retrieval."""
        # Step 1: Summarize conversation
        summary = summarizer_with_mock_client.summarize_messages(
            sample_conversation,
            max_length=500
        )
        assert len(summary) > 0

        # Step 2: Store summary (simulate)
        stored_summary = {
            "id": "mem_full_cycle",
            "content": summary,
            "metadata": {
                "session_id": "session-full-cycle",
                "message_range": "1-12",
                "domain": "conversation_summary",
                "original_token_count": summarizer_with_mock_client.count_message_tokens(sample_conversation),
                "summary_token_count": summarizer_with_mock_client.count_tokens(summary)
            },
            "created_at": datetime.now().isoformat()
        }
        optimizer_with_mock_memory.memory_service._stored_summaries.append(stored_summary)

        # Step 3: Retrieve context
        context = optimizer_with_mock_memory.retrieve_relevant_context(
            current_prompt="Tell me about our authentication discussion",
            session_id="session-full-cycle"
        )

        assert context["count"] > 0
        assert any("authentication" in mem.get("memory", "").lower()
                   for mem in context["memories"])

    def test_progressive_summarization_multiple_chunks(
        self,
        summarizer_with_mock_client,
        long_conversation
    ):
        """Test: Progressive summarization of very long conversations."""
        # Group messages into chunks
        token_limit = 1000
        groups = summarizer_with_mock_client.group_messages_by_token_limit(
            long_conversation,
            token_limit=token_limit
        )

        assert len(groups) > 1  # Should create multiple groups

        # Mock multiple summary responses
        summarizer_with_mock_client.llm_client.chat = Mock(
            return_value="Summary of conversation chunk"
        )

        # Summarize each chunk
        summaries = []
        for i, group in enumerate(groups):
            summary = summarizer_with_mock_client.summarize_messages(group)
            summaries.append({
                "content": summary,
                "message_range": f"{i*50+1}-{(i+1)*50}",
                "chunk": i
            })

        assert len(summaries) == len(groups)
        assert all(s["content"] for s in summaries)


# =============================================================================
# Test Context Window Management
# =============================================================================

class TestContextWindowManagement:
    """Test token limit handling and context window optimization."""

    def test_detect_context_window_threshold(
        self,
        summarizer_with_mock_client,
        long_conversation
    ):
        """Test: Detect when context window approaches limit."""
        # Simulate context window limit (e.g., 100k tokens)
        context_limit = 100000
        warning_threshold = int(context_limit * 0.8)  # 80% threshold

        total_tokens = summarizer_with_mock_client.count_message_tokens(long_conversation)

        # Check if we need to summarize
        should_summarize = total_tokens > warning_threshold

        if should_summarize:
            # Calculate how many messages to summarize
            preserve_recent = 20  # Keep last 20 messages
            messages_to_summarize = long_conversation[:-preserve_recent]

            summary = summarizer_with_mock_client.summarize_messages(
                messages_to_summarize,
                preserve_recent=0
            )

            assert isinstance(summary, str)
            assert len(summary) > 0

    def test_token_budget_enforcement_during_injection(
        self,
        optimizer_with_mock_memory
    ):
        """Test: Context injection respects token budget."""
        # Create many large summaries
        large_summaries = []
        for i in range(20):
            large_summaries.append({
                "id": f"mem_{i}",
                "content": f"Large summary {i}. " * 100,
                "metadata": {
                    "session_id": "session-budget",
                    "message_range": f"{i*10+1}-{(i+1)*10}",
                    "domain": "conversation_summary"
                },
                "created_at": datetime.now().isoformat()
            })

        optimizer_with_mock_memory.memory_service._stored_summaries.extend(large_summaries)

        # Retrieve with strict token budget
        max_tokens = 500
        context = optimizer_with_mock_memory.retrieve_relevant_context(
            current_prompt="test query",
            max_tokens=max_tokens
        )

        # Should not exceed budget (with 10% tolerance)
        assert context["token_count"] <= max_tokens * 1.1

    def test_preserve_recent_messages_during_summarization(
        self,
        summarizer_with_mock_client,
        sample_conversation
    ):
        """Test: Recent messages preserved during summarization."""
        preserve_count = 4

        # Summarize older messages, preserve recent ones
        summary = summarizer_with_mock_client.summarize_messages(
            sample_conversation,
            preserve_recent=preserve_count
        )

        # Should only summarize first 8 messages (12 total - 4 preserved)
        if len(sample_conversation) <= preserve_count:
            assert summary == ""
        else:
            assert isinstance(summary, str)


# =============================================================================
# Test Multi-Session Integration
# =============================================================================

class TestMultiSessionIntegration:
    """Test context optimization across multiple conversation sessions."""

    def test_retrieve_context_from_previous_session(
        self,
        optimizer_with_mock_memory
    ):
        """Test: Retrieve context from earlier sessions."""
        # Simulate summaries from different sessions
        optimizer_with_mock_memory.memory_service._stored_summaries.extend([
            {
                "id": "mem_old_session",
                "content": "Previous session discussed OAuth2 authentication.",
                "metadata": {
                    "session_id": "session-old",
                    "message_range": "1-50",
                    "domain": "conversation_summary"
                },
                "created_at": (datetime.now() - timedelta(days=2)).isoformat()
            },
            {
                "id": "mem_current_session",
                "content": "Current session discussing JWT implementation.",
                "metadata": {
                    "session_id": "session-current",
                    "message_range": "1-30",
                    "domain": "conversation_summary"
                },
                "created_at": datetime.now().isoformat()
            }
        ])

        # Retrieve context without session filter
        context = optimizer_with_mock_memory.retrieve_relevant_context(
            current_prompt="authentication approaches",
            include_session_only=False
        )

        # Should retrieve from both sessions
        assert context["count"] > 0

    def test_session_specific_context_retrieval(
        self,
        optimizer_with_mock_memory
    ):
        """Test: Filter context to specific session only."""
        # Add summaries from multiple sessions
        optimizer_with_mock_memory.memory_service._stored_summaries.extend([
            {
                "id": "mem_session_a",
                "content": "Session A content.",
                "metadata": {
                    "session_id": "session-a",
                    "message_range": "1-10",
                    "domain": "conversation_summary"
                },
                "created_at": datetime.now().isoformat()
            },
            {
                "id": "mem_session_b",
                "content": "Session B content.",
                "metadata": {
                    "session_id": "session-b",
                    "message_range": "1-10",
                    "domain": "conversation_summary"
                },
                "created_at": datetime.now().isoformat()
            }
        ])

        # Retrieve only from session-a
        context = optimizer_with_mock_memory.retrieve_relevant_context(
            current_prompt="test",
            session_id="session-a",
            include_session_only=True
        )

        # Verify results are from session-a only
        for memory in context["memories"]:
            session_id = optimizer_with_mock_memory._extract_session_id(memory)
            if session_id:
                assert session_id == "session-a"


# =============================================================================
# Test Performance Under Load
# =============================================================================

class TestPerformanceUnderLoad:
    """Test performance with high-volume conversations."""

    def test_summarize_large_conversation_performance(
        self,
        summarizer_with_mock_client,
        long_conversation
    ):
        """Test: Summarization performance with large conversations."""
        import time

        start_time = time.time()

        # Summarize 200 messages
        summary = summarizer_with_mock_client.summarize_messages(
            long_conversation,
            max_length=1000
        )

        elapsed_ms = (time.time() - start_time) * 1000

        # Should complete reasonably fast (mocked, so very fast)
        assert elapsed_ms < 5000  # 5 seconds max
        assert isinstance(summary, str)

    def test_retrieval_performance_many_summaries(
        self,
        optimizer_with_mock_memory
    ):
        """Test: Retrieval performance with many stored summaries."""
        import time

        # Add 100 summaries
        for i in range(100):
            optimizer_with_mock_memory.memory_service._stored_summaries.append({
                "id": f"mem_perf_{i}",
                "content": f"Summary {i} about various topics.",
                "metadata": {
                    "session_id": f"session-{i % 10}",
                    "message_range": f"{i*10+1}-{(i+1)*10}",
                    "domain": "conversation_summary"
                },
                "created_at": datetime.now().isoformat()
            })

        start_time = time.time()

        context = optimizer_with_mock_memory.retrieve_relevant_context(
            current_prompt="test query"
        )

        elapsed_ms = (time.time() - start_time) * 1000

        # Should retrieve quickly even with many summaries
        assert elapsed_ms < 2000  # 2 seconds max
        assert context["retrieval_time_ms"] >= 0


# =============================================================================
# Test Error Handling and Edge Cases
# =============================================================================

class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_summarization_fails_gracefully_without_llm(
        self,
        sample_conversation
    ):
        """Test: Summarization handles missing LLM client."""
        summarizer = ConversationSummarizer()
        summarizer.llm_client = None

        with pytest.raises(RuntimeError, match="LLM client not available"):
            summarizer.summarize_messages(sample_conversation)

    def test_retrieval_fails_gracefully_without_memory(
        self,
        sample_conversation
    ):
        """Test: Retrieval handles missing Memory V2."""
        optimizer = ContextOptimizer()
        optimizer.memory_service = None

        with pytest.raises(RuntimeError, match="Memory V2 not available"):
            optimizer.retrieve_relevant_context(
                current_prompt="test"
            )

    def test_summarization_with_llm_error_uses_fallback(
        self,
        summarizer_with_mock_client,
        sample_conversation
    ):
        """Test: LLM errors trigger fallback summarization."""
        # Make LLM call fail
        summarizer_with_mock_client.llm_client.chat.side_effect = Exception("API Error")

        summary = summarizer_with_mock_client.summarize_messages(sample_conversation)

        # Should return fallback summary
        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_retrieval_with_search_error_returns_empty(
        self,
        optimizer_with_mock_memory
    ):
        """Test: Search errors return empty results gracefully."""
        # Make search fail
        optimizer_with_mock_memory.memory_service.search.side_effect = Exception("Search failed")

        context = optimizer_with_mock_memory.retrieve_relevant_context(
            current_prompt="test"
        )

        # Should return empty result with error
        assert context["count"] == 0
        assert "error" in context

    def test_empty_conversation_summarization(
        self,
        summarizer_with_mock_client
    ):
        """Test: Empty conversations handled gracefully."""
        summary = summarizer_with_mock_client.summarize_messages([])

        assert summary == ""

    def test_empty_context_retrieval(
        self,
        optimizer_with_mock_memory
    ):
        """Test: Retrieval with no stored summaries."""
        # No summaries in storage
        optimizer_with_mock_memory.memory_service._stored_summaries.clear()

        context = optimizer_with_mock_memory.retrieve_relevant_context(
            current_prompt="test"
        )

        assert context["count"] == 0
        assert context["memories"] == []
        assert context["formatted_context"] == ""


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
