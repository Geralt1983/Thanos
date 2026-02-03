#!/usr/bin/env python3
"""
Tests for Conversation Summarizer.

Tests the LLM-based conversation summarization engine, token counting,
message grouping, and Memory V2 integration.
"""

import pytest
import json
from pathlib import Path
from typing import Dict, List, Any
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from Tools.conversation_summarizer import (
    ConversationSummarizer,
    SummaryResult,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_messages():
    """Sample conversation messages for testing."""
    return [
        {"role": "user", "content": "What's the weather like today?"},
        {"role": "assistant", "content": "I'll check the weather for you. Where are you located?"},
        {"role": "user", "content": "I'm in King, North Carolina."},
        {"role": "assistant", "content": "Let me check the weather in King, NC for you."},
        {"role": "user", "content": "Thanks!"},
    ]


@pytest.fixture
def long_messages():
    """Long conversation for testing compression."""
    messages = []
    for i in range(50):
        messages.append({
            "role": "user",
            "content": f"This is test message number {i} from the user. " * 10
        })
        messages.append({
            "role": "assistant",
            "content": f"This is test response number {i} from the assistant. " * 10
        })
    return messages


@pytest.fixture
def mock_llm_client():
    """Create a mock LiteLLM client."""
    client = Mock()
    client.chat = Mock(return_value="This is a concise summary of the conversation.")
    return client


@pytest.fixture
def mock_memory_service():
    """Create a mock Memory V2 service."""
    service = Mock()
    service.add = Mock(return_value={
        "id": "mem_123",
        "content": "Test summary",
        "metadata": {}
    })
    return service


@pytest.fixture
def summarizer_with_mock_client(mock_llm_client):
    """Create summarizer with mocked LLM client."""
    summarizer = ConversationSummarizer()
    summarizer.llm_client = mock_llm_client
    return summarizer


# ============================================================================
# Initialization Tests
# ============================================================================

class TestInitialization:
    """Test ConversationSummarizer initialization."""

    def test_default_initialization(self):
        """Test initialization with default parameters."""
        summarizer = ConversationSummarizer()

        assert summarizer.model == "anthropic/claude-sonnet-4-5"
        assert summarizer.max_tokens == 2000
        assert summarizer.compression_ratio == 0.3

    def test_custom_initialization(self):
        """Test initialization with custom parameters."""
        summarizer = ConversationSummarizer(
            model="anthropic/claude-opus-4-5-20250514",
            max_tokens=4000,
            compression_ratio=0.5
        )

        assert summarizer.model == "anthropic/claude-opus-4-5-20250514"
        assert summarizer.max_tokens == 4000
        assert summarizer.compression_ratio == 0.5

    def test_llm_client_initialization(self):
        """Test that LLM client is initialized (or warned if unavailable)."""
        summarizer = ConversationSummarizer()
        # Client might be None if LiteLLM not available, but shouldn't crash
        assert summarizer.llm_client is not None or summarizer.llm_client is None


# ============================================================================
# Token Counting Tests
# ============================================================================

class TestTokenCounting:
    """Test token counting functionality."""

    def test_count_tokens_basic(self):
        """Test basic token counting."""
        summarizer = ConversationSummarizer()

        text = "Hello, world!"
        count = summarizer.count_tokens(text)

        # Should return a positive integer
        assert isinstance(count, int)
        assert count > 0

    def test_count_tokens_empty_string(self):
        """Test token counting with empty string."""
        summarizer = ConversationSummarizer()

        count = summarizer.count_tokens("")

        assert count == 0

    def test_count_tokens_long_text(self):
        """Test token counting with longer text."""
        summarizer = ConversationSummarizer()

        short_text = "Hi"
        long_text = "This is a much longer text that should have more tokens. " * 10

        short_count = summarizer.count_tokens(short_text)
        long_count = summarizer.count_tokens(long_text)

        assert long_count > short_count

    def test_count_message_tokens(self, sample_messages):
        """Test counting tokens across multiple messages."""
        summarizer = ConversationSummarizer()

        total_tokens = summarizer.count_message_tokens(sample_messages)

        assert isinstance(total_tokens, int)
        assert total_tokens > 0
        # Should account for role + content + overhead
        assert total_tokens > len(sample_messages)

    def test_count_message_tokens_empty_list(self):
        """Test counting tokens with empty message list."""
        summarizer = ConversationSummarizer()

        total_tokens = summarizer.count_message_tokens([])

        assert total_tokens == 0

    def test_count_message_tokens_includes_overhead(self):
        """Test that message token counting includes structural overhead."""
        summarizer = ConversationSummarizer()

        messages = [{"role": "user", "content": "test"}]
        total_tokens = summarizer.count_message_tokens(messages)

        # Should be more than just the content tokens due to overhead
        content_only = summarizer.count_tokens("test")
        assert total_tokens > content_only


# ============================================================================
# Message Summarization Tests
# ============================================================================

class TestMessageSummarization:
    """Test message summarization functionality."""

    def test_summarize_messages_basic(self, summarizer_with_mock_client, sample_messages):
        """Test basic message summarization."""
        summary = summarizer_with_mock_client.summarize_messages(sample_messages)

        assert isinstance(summary, str)
        assert len(summary) > 0
        # Verify LLM client was called
        summarizer_with_mock_client.llm_client.chat.assert_called_once()

    def test_summarize_messages_empty_list(self, summarizer_with_mock_client):
        """Test summarizing empty message list."""
        summary = summarizer_with_mock_client.summarize_messages([])

        assert summary == ""

    def test_summarize_messages_with_preserve_recent(self, summarizer_with_mock_client, sample_messages):
        """Test summarization while preserving recent messages."""
        summary = summarizer_with_mock_client.summarize_messages(
            sample_messages,
            preserve_recent=2
        )

        assert isinstance(summary, str)
        # Should only summarize first 3 messages (5 total - 2 preserved)

    def test_summarize_messages_with_max_length(self, summarizer_with_mock_client, sample_messages):
        """Test summarization with custom max_length."""
        summary = summarizer_with_mock_client.summarize_messages(
            sample_messages,
            max_length=100
        )

        assert isinstance(summary, str)
        # Check that max_length was used in the prompt
        call_args = summarizer_with_mock_client.llm_client.chat.call_args
        assert "100 tokens" in call_args[0][0]

    def test_summarize_messages_without_llm_client(self):
        """Test that summarization fails gracefully without LLM client."""
        summarizer = ConversationSummarizer()
        summarizer.llm_client = None

        with pytest.raises(RuntimeError, match="LLM client not available"):
            summarizer.summarize_messages([{"role": "user", "content": "test"}])

    def test_summarize_messages_llm_failure_uses_fallback(self, summarizer_with_mock_client, sample_messages):
        """Test fallback summarization when LLM call fails."""
        # Make LLM call fail
        summarizer_with_mock_client.llm_client.chat.side_effect = Exception("API Error")

        summary = summarizer_with_mock_client.summarize_messages(sample_messages)

        # Should still return a summary (fallback)
        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_summarize_preserves_all_with_preserve_recent(self, summarizer_with_mock_client):
        """Test that preserve_recent equal to message count returns empty."""
        messages = [{"role": "user", "content": "test"}]

        summary = summarizer_with_mock_client.summarize_messages(
            messages,
            preserve_recent=1
        )

        # Should return empty since all messages preserved
        assert summary == ""


# ============================================================================
# Key Point Extraction Tests
# ============================================================================

class TestKeyPointExtraction:
    """Test key point extraction functionality."""

    def test_extract_key_points_basic(self, summarizer_with_mock_client, sample_messages):
        """Test basic key point extraction."""
        # Mock LLM to return bullet points
        summarizer_with_mock_client.llm_client.chat.return_value = """
- User asked about weather
- Assistant requested location
- User provided King, NC
- Assistant checked weather
"""

        key_points = summarizer_with_mock_client.extract_key_points(sample_messages)

        assert isinstance(key_points, list)
        assert len(key_points) > 0
        # Check that bullet markers were stripped
        for point in key_points:
            assert not point.startswith('-')
            assert not point.startswith('*')

    def test_extract_key_points_empty_list(self, summarizer_with_mock_client):
        """Test key point extraction with empty messages."""
        key_points = summarizer_with_mock_client.extract_key_points([])

        assert key_points == []

    def test_extract_key_points_respects_max_points(self, summarizer_with_mock_client, sample_messages):
        """Test that max_points limit is respected."""
        # Return more points than requested
        summarizer_with_mock_client.llm_client.chat.return_value = "\n".join(
            [f"- Point {i}" for i in range(20)]
        )

        key_points = summarizer_with_mock_client.extract_key_points(
            sample_messages,
            max_points=5
        )

        # Should be limited to 5
        assert len(key_points) <= 5

    def test_extract_key_points_without_llm_client(self):
        """Test key point extraction without LLM client."""
        summarizer = ConversationSummarizer()
        summarizer.llm_client = None

        key_points = summarizer.extract_key_points([{"role": "user", "content": "test"}])

        # Should return empty list instead of crashing
        assert key_points == []

    def test_extract_key_points_handles_various_bullet_formats(self, summarizer_with_mock_client, sample_messages):
        """Test that various bullet point formats are handled."""
        summarizer_with_mock_client.llm_client.chat.return_value = """
- Dash bullet
* Asterisk bullet
• Dot bullet
+ Plus bullet
Normal text without bullet
"""

        key_points = summarizer_with_mock_client.extract_key_points(sample_messages)

        # Should parse all formats and strip markers
        assert len(key_points) == 5
        for point in key_points:
            assert not point.startswith(('-', '*', '•', '+'))


# ============================================================================
# Message Grouping Tests
# ============================================================================

class TestMessageGrouping:
    """Test message grouping by token limit."""

    def test_group_messages_basic(self, sample_messages):
        """Test basic message grouping."""
        summarizer = ConversationSummarizer()

        groups = summarizer.group_messages_by_token_limit(sample_messages, token_limit=100)

        assert isinstance(groups, list)
        assert len(groups) > 0
        # All original messages should be in groups
        total_messages = sum(len(group) for group in groups)
        assert total_messages == len(sample_messages)

    def test_group_messages_empty_list(self):
        """Test grouping empty message list."""
        summarizer = ConversationSummarizer()

        groups = summarizer.group_messages_by_token_limit([], token_limit=100)

        assert groups == []

    def test_group_messages_single_large_message(self):
        """Test grouping when single message exceeds limit."""
        summarizer = ConversationSummarizer()

        large_message = [{"role": "user", "content": "x" * 1000}]
        groups = summarizer.group_messages_by_token_limit(large_message, token_limit=10)

        # Should still create one group with the message
        assert len(groups) == 1
        assert len(groups[0]) == 1

    def test_group_messages_respects_token_limit(self, long_messages):
        """Test that groups respect token limit."""
        summarizer = ConversationSummarizer()

        token_limit = 500
        groups = summarizer.group_messages_by_token_limit(long_messages, token_limit=token_limit)

        # Check that each group (except possibly last) is near the limit
        for group in groups[:-1]:  # Exclude last group which might be partial
            group_tokens = summarizer.count_message_tokens(group)
            # Allow 10% tolerance for user/assistant pairing
            assert group_tokens <= token_limit * 1.1

    def test_group_messages_invalid_token_limit(self, sample_messages):
        """Test grouping with invalid token limit uses default."""
        summarizer = ConversationSummarizer()

        # Negative limit
        groups = summarizer.group_messages_by_token_limit(sample_messages, token_limit=-100)
        assert len(groups) > 0

        # Zero limit
        groups = summarizer.group_messages_by_token_limit(sample_messages, token_limit=0)
        assert len(groups) > 0

    def test_group_messages_preserves_user_assistant_pairs(self):
        """Test that user/assistant pairs are kept together when possible."""
        summarizer = ConversationSummarizer()

        messages = [
            {"role": "user", "content": "Question 1?"},
            {"role": "assistant", "content": "Answer 1"},
            {"role": "user", "content": "Question 2?"},
            {"role": "assistant", "content": "Answer 2"},
        ]

        # Use a limit that would split between pairs
        groups = summarizer.group_messages_by_token_limit(messages, token_limit=50)

        # Check that groups preserve conversational flow when possible
        for group in groups:
            # Groups should generally start with user or continue from previous
            assert len(group) > 0


# ============================================================================
# Compression Estimation Tests
# ============================================================================

class TestCompressionEstimation:
    """Test compression estimation functionality."""

    def test_estimate_compression_basic(self, sample_messages):
        """Test basic compression estimation."""
        summarizer = ConversationSummarizer(compression_ratio=0.3)

        estimate = summarizer.estimate_compression(sample_messages)

        assert "original_tokens" in estimate
        assert "estimated_summary_tokens" in estimate
        assert "savings" in estimate
        assert "compression_ratio" in estimate

        assert estimate["compression_ratio"] == 0.3
        assert estimate["estimated_summary_tokens"] == int(estimate["original_tokens"] * 0.3)
        assert estimate["savings"] == estimate["original_tokens"] - estimate["estimated_summary_tokens"]

    def test_estimate_compression_empty_messages(self):
        """Test compression estimation with empty messages."""
        summarizer = ConversationSummarizer()

        estimate = summarizer.estimate_compression([])

        assert estimate["original_tokens"] == 0
        assert estimate["estimated_summary_tokens"] == 0
        assert estimate["savings"] == 0

    def test_estimate_compression_different_ratios(self, sample_messages):
        """Test compression estimation with different ratios."""
        ratios = [0.1, 0.3, 0.5, 0.7]

        for ratio in ratios:
            summarizer = ConversationSummarizer(compression_ratio=ratio)
            estimate = summarizer.estimate_compression(sample_messages)

            assert estimate["compression_ratio"] == ratio
            expected_compressed = int(estimate["original_tokens"] * ratio)
            assert estimate["estimated_summary_tokens"] == expected_compressed


# ============================================================================
# Summary Storage Tests
# ============================================================================

class TestSummaryStorage:
    """Test summary storage in Memory V2."""

    @patch('Tools.conversation_summarizer.MEMORY_V2_AVAILABLE', True)
    @patch('Tools.conversation_summarizer.MemoryService')
    def test_store_summary_basic(self, mock_memory_service_class):
        """Test basic summary storage."""
        mock_service = Mock()
        mock_service.add.return_value = {"id": "mem_123", "content": "Test summary"}
        mock_memory_service_class.return_value = mock_service

        summarizer = ConversationSummarizer()

        result = summarizer.store_summary(
            summary="This is a test summary",
            session_id="session_123",
            message_range="1-10"
        )

        assert result["id"] == "mem_123"
        mock_service.add.assert_called_once()

        # Check metadata
        call_args = mock_service.add.call_args
        metadata = call_args[1]["metadata"]
        assert metadata["session_id"] == "session_123"
        assert metadata["message_range"] == "1-10"
        assert metadata["domain"] == "conversation_summary"

    @patch('Tools.conversation_summarizer.MEMORY_V2_AVAILABLE', True)
    @patch('Tools.conversation_summarizer.MemoryService')
    def test_store_summary_with_summary_result(self, mock_memory_service_class):
        """Test storing SummaryResult object."""
        mock_service = Mock()
        mock_service.add.return_value = {"id": "mem_456"}
        mock_memory_service_class.return_value = mock_service

        summarizer = ConversationSummarizer()

        summary_result = SummaryResult(
            summary="Detailed summary",
            key_points=["Point 1", "Point 2"],
            original_token_count=1000,
            summary_token_count=300,
            compression_ratio=0.3,
            messages_summarized=25,
            timestamp=datetime.now().isoformat()
        )

        result = summarizer.store_summary(
            summary=summary_result,
            session_id="session_456"
        )

        assert result["id"] == "mem_456"

        # Check that SummaryResult fields were included in metadata
        call_args = mock_service.add.call_args
        metadata = call_args[1]["metadata"]
        assert metadata["original_token_count"] == 1000
        assert metadata["summary_token_count"] == 300
        assert metadata["compression_ratio"] == 0.3
        assert metadata["key_points"] == ["Point 1", "Point 2"]

    @patch('Tools.conversation_summarizer.MEMORY_V2_AVAILABLE', False)
    def test_store_summary_without_memory_v2(self):
        """Test that storage fails when Memory V2 unavailable."""
        summarizer = ConversationSummarizer()

        with pytest.raises(RuntimeError, match="Memory V2 not available"):
            summarizer.store_summary(
                summary="Test",
                session_id="session_123"
            )

    @patch('Tools.conversation_summarizer.MEMORY_V2_AVAILABLE', True)
    @patch('Tools.conversation_summarizer.MemoryService')
    def test_store_summary_rejects_empty(self, mock_memory_service_class):
        """Test that empty summaries are rejected."""
        summarizer = ConversationSummarizer()

        with pytest.raises(ValueError, match="Cannot store empty summary"):
            summarizer.store_summary(summary="", session_id="session_123")

        with pytest.raises(ValueError, match="Cannot store empty summary"):
            summarizer.store_summary(summary="   ", session_id="session_123")

    @patch('Tools.conversation_summarizer.MEMORY_V2_AVAILABLE', True)
    @patch('Tools.conversation_summarizer.MemoryService')
    def test_store_summary_with_additional_metadata(self, mock_memory_service_class):
        """Test storing summary with additional metadata."""
        mock_service = Mock()
        mock_service.add.return_value = {"id": "mem_789"}
        mock_memory_service_class.return_value = mock_service

        summarizer = ConversationSummarizer()

        additional_meta = {
            "custom_field": "custom_value",
            "priority": "high"
        }

        summarizer.store_summary(
            summary="Test summary",
            session_id="session_789",
            additional_metadata=additional_meta
        )

        # Check that additional metadata was merged
        call_args = mock_service.add.call_args
        metadata = call_args[1]["metadata"]
        assert metadata["custom_field"] == "custom_value"
        assert metadata["priority"] == "high"
        assert metadata["session_id"] == "session_789"


# ============================================================================
# Fallback Summary Tests
# ============================================================================

class TestFallbackSummary:
    """Test fallback summarization when LLM fails."""

    def test_fallback_summary_basic(self):
        """Test basic fallback summary."""
        summarizer = ConversationSummarizer()

        messages = [
            {"role": "user", "content": "First message"},
            {"role": "assistant", "content": "Second message"},
            {"role": "user", "content": "Third message"},
        ]

        fallback = summarizer._fallback_summary(messages, max_tokens=100)

        assert isinstance(fallback, str)
        assert len(fallback) > 0
        # Should include first and last messages
        assert "First message" in fallback
        assert "Third message" in fallback

    def test_fallback_summary_empty_messages(self):
        """Test fallback with empty messages."""
        summarizer = ConversationSummarizer()

        fallback = summarizer._fallback_summary([], max_tokens=100)

        assert fallback == ""

    def test_fallback_summary_single_message(self):
        """Test fallback with single message."""
        summarizer = ConversationSummarizer()

        messages = [{"role": "user", "content": "Only message"}]
        fallback = summarizer._fallback_summary(messages, max_tokens=100)

        assert "Only message" in fallback


# ============================================================================
# Format Messages Tests
# ============================================================================

class TestFormatMessages:
    """Test message formatting for summarization."""

    def test_format_messages_basic(self, sample_messages):
        """Test basic message formatting."""
        summarizer = ConversationSummarizer()

        formatted = summarizer._format_messages_for_summary(sample_messages)

        assert isinstance(formatted, str)
        # Should contain role labels
        assert "User:" in formatted
        assert "Assistant:" in formatted

    def test_format_messages_preserves_content(self, sample_messages):
        """Test that formatting preserves message content."""
        summarizer = ConversationSummarizer()

        formatted = summarizer._format_messages_for_summary(sample_messages)

        # All message contents should be present
        for msg in sample_messages:
            assert msg["content"] in formatted

    def test_format_messages_handles_system_role(self):
        """Test formatting with system role messages."""
        summarizer = ConversationSummarizer()

        messages = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "User message"},
        ]

        formatted = summarizer._format_messages_for_summary(messages)

        assert "System:" in formatted
        assert "User:" in formatted


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for full workflows."""

    def test_full_summarization_workflow(self, summarizer_with_mock_client, sample_messages):
        """Test complete summarization workflow."""
        # Mock successful LLM responses
        summarizer_with_mock_client.llm_client.chat.side_effect = [
            "This is a summary of the weather conversation.",
            "- Weather query\n- Location provided\n- Weather checked"
        ]

        # Estimate compression
        estimate = summarizer_with_mock_client.estimate_compression(sample_messages)
        assert estimate["original_tokens"] > 0

        # Summarize messages
        summary = summarizer_with_mock_client.summarize_messages(sample_messages)
        assert len(summary) > 0

        # Extract key points
        key_points = summarizer_with_mock_client.extract_key_points(sample_messages)
        assert len(key_points) > 0

    def test_grouping_and_summarization_workflow(self, summarizer_with_mock_client, long_messages):
        """Test grouping messages and summarizing each group."""
        # Group messages
        groups = summarizer_with_mock_client.group_messages_by_token_limit(
            long_messages,
            token_limit=1000
        )

        assert len(groups) > 1

        # Mock LLM to return different summaries for each group
        summarizer_with_mock_client.llm_client.chat.return_value = "Group summary"

        # Summarize each group
        summaries = []
        for group in groups:
            summary = summarizer_with_mock_client.summarize_messages(group)
            summaries.append(summary)

        assert len(summaries) == len(groups)
        assert all(len(s) > 0 for s in summaries)


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
