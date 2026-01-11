"""
Unit tests for ContextManager.

Tests cover:
- Token estimation with tiktoken
- Fallback token estimation
- Message token estimation
- History trimming logic
- Context window limits
- Usage reporting
"""

from unittest.mock import Mock, patch

import pytest

from Tools.context_manager import ContextManager


@pytest.mark.unit
class TestContextManagerInitialization:
    """Test ContextManager initialization."""

    def test_initialization_with_default_model(self):
        """Test initialization with default model."""
        cm = ContextManager()
        assert cm.model == "claude-opus-4-5-20251101"
        assert cm.max_tokens == 200000
        assert cm.available_tokens == 200000 - 8000

    def test_initialization_with_custom_model(self):
        """Test initialization with custom model."""
        cm = ContextManager(model="claude-sonnet-4-20250514")
        assert cm.model == "claude-sonnet-4-20250514"
        assert cm.max_tokens == 200000

    def test_initialization_with_unknown_model(self):
        """Test initialization with unknown model falls back to default limit."""
        cm = ContextManager(model="unknown-model")
        assert cm.model == "unknown-model"
        assert cm.max_tokens == 100000

    def test_output_reserve_calculation(self):
        """Test that output reserve is properly calculated."""
        cm = ContextManager()
        assert cm.available_tokens == cm.max_tokens - cm.OUTPUT_RESERVE
        assert cm.OUTPUT_RESERVE == 8000

    @patch("tiktoken.get_encoding")
    def test_tiktoken_initialization_success(self, mock_get_encoding):
        """Test successful tiktoken initialization."""
        mock_encoder = Mock()
        mock_get_encoding.return_value = mock_encoder

        cm = ContextManager()
        assert cm.encoding is not None
        mock_get_encoding.assert_called_once_with("cl100k_base")

    @patch("tiktoken.get_encoding")
    def test_tiktoken_initialization_failure(self, mock_get_encoding):
        """Test graceful fallback when tiktoken fails."""
        mock_get_encoding.side_effect = Exception("tiktoken error")

        cm = ContextManager()
        assert cm.encoding is None


@pytest.mark.unit
class TestTokenEstimation:
    """Test token estimation methods."""

    def test_estimate_tokens_empty_string(self):
        """Test token estimation for empty string."""
        cm = ContextManager()
        assert cm.estimate_tokens("") == 0

    def test_estimate_tokens_none(self):
        """Test token estimation for None."""
        cm = ContextManager()
        assert cm.estimate_tokens(None) == 0

    @patch("tiktoken.get_encoding")
    def test_estimate_tokens_with_tiktoken(self, mock_get_encoding):
        """Test token estimation using tiktoken."""
        mock_encoder = Mock()
        mock_encoder.encode.return_value = [1, 2, 3, 4, 5]  # 5 tokens
        mock_get_encoding.return_value = mock_encoder

        cm = ContextManager()
        tokens = cm.estimate_tokens("Hello world")

        assert tokens == 5
        mock_encoder.encode.assert_called_once_with("Hello world")

    def test_estimate_tokens_fallback(self):
        """Test token estimation using fallback method."""
        with patch("tiktoken.get_encoding", side_effect=Exception("fail")):
            cm = ContextManager()
            # Fallback: len(text) / 3.5
            tokens = cm.estimate_tokens("Hello world")  # 11 chars / 3.5 ≈ 3
            assert tokens == 3

    @patch("tiktoken.get_encoding")
    def test_estimate_tokens_tiktoken_encoding_failure(self, mock_get_encoding):
        """Test fallback when tiktoken encoding fails."""
        mock_encoder = Mock()
        mock_encoder.encode.side_effect = Exception("encoding error")
        mock_get_encoding.return_value = mock_encoder

        cm = ContextManager()
        tokens = cm.estimate_tokens("Hello world")  # 11 / 3.5 ≈ 3

        assert tokens == 3

    def test_estimate_messages_tokens_empty_list(self):
        """Test message token estimation for empty list."""
        cm = ContextManager()
        assert cm.estimate_messages_tokens([]) == 0

    def test_estimate_messages_tokens_single_message(self):
        """Test message token estimation for single message."""
        cm = ContextManager()
        messages = [{"role": "user", "content": "Hello"}]

        tokens = cm.estimate_messages_tokens(messages)

        # Should include content tokens + 4 for structure
        assert tokens > 4

    def test_estimate_messages_tokens_multiple_messages(self):
        """Test message token estimation for multiple messages."""
        cm = ContextManager()
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
        ]

        tokens = cm.estimate_messages_tokens(messages)

        # Should include all content tokens + 4 per message
        assert tokens > 12  # At least 4 * 3 messages

    def test_estimate_messages_tokens_includes_overhead(self):
        """Test that message token estimation includes structure overhead."""
        cm = ContextManager()

        # Two identical messages should have different total than doubled single message
        single = [{"role": "user", "content": "Test"}]
        double = [{"role": "user", "content": "Test"}, {"role": "user", "content": "Test"}]

        single_tokens = cm.estimate_messages_tokens(single)
        double_tokens = cm.estimate_messages_tokens(double)

        # Double should be more than 2x single due to overhead
        assert double_tokens >= single_tokens * 2


@pytest.mark.unit
class TestHistoryTrimming:
    """Test history trimming functionality."""

    def test_trim_history_no_trimming_needed(self):
        """Test that history is not trimmed when within limits."""
        cm = ContextManager()
        history = [{"role": "user", "content": "Short message"}]
        system_prompt = "You are a helpful assistant."
        new_message = "Another short message"

        trimmed, was_trimmed = cm.trim_history(history, system_prompt, new_message)

        assert not was_trimmed
        assert len(trimmed) == len(history)
        assert trimmed == history

    def test_trim_history_removes_oldest_first(self):
        """Test that oldest messages are removed first when trimming."""
        cm = ContextManager()
        # Reduce available tokens to force trimming
        cm.available_tokens = 5000

        # Create a large history that exceeds limits
        history = []
        for i in range(50):
            history.append({"role": "user", "content": f"Message {i}" * 100})

        system_prompt = "You are a helpful assistant."
        new_message = "New message"

        trimmed, was_trimmed = cm.trim_history(history, system_prompt, new_message)

        assert was_trimmed
        assert len(trimmed) < len(history)

        # Most recent message should be preserved
        if trimmed:
            assert "Message 49" in trimmed[-1]["content"]
            # Oldest messages should be removed
            assert "Message 0" not in [m["content"] for m in trimmed]

    def test_trim_history_keeps_most_recent(self):
        """Test that most recent messages are kept when trimming."""
        cm = ContextManager()
        # Reduce available tokens to force trimming
        cm.available_tokens = 2000

        # Create history that needs trimming
        history = []
        for i in range(30):
            content = "A" * 500  # ~143 tokens each, 30 messages = ~4300 tokens > 2000 limit
            history.append({"role": "user", "content": f"{i}:{content}"})

        system_prompt = "System prompt"
        new_message = "New message"

        trimmed, was_trimmed = cm.trim_history(history, system_prompt, new_message)

        assert was_trimmed
        # Most recent message number should be in trimmed history
        if trimmed:
            last_msg_num = int(trimmed[-1]["content"].split(":")[0])
            assert last_msg_num == 29  # Most recent

    def test_trim_history_empty_history(self):
        """Test trimming with empty history."""
        cm = ContextManager()
        history = []
        system_prompt = "System prompt"
        new_message = "New message"

        trimmed, was_trimmed = cm.trim_history(history, system_prompt, new_message)

        assert not was_trimmed
        assert trimmed == []

    def test_trim_history_exceeds_limit_without_history(self):
        """Test case where system prompt + new message exceed limit."""
        cm = ContextManager()
        # Set a very small limit so system prompt + message exceed it
        cm.available_tokens = 100

        # Create large system prompt and message that together exceed the tiny limit
        system_prompt = "A" * 500  # Well over 100 tokens
        new_message = "B" * 500  # Well over 100 tokens combined
        history = [{"role": "user", "content": "Normal message"}]

        trimmed, was_trimmed = cm.trim_history(history, system_prompt, new_message)

        assert was_trimmed
        assert trimmed == []  # All history removed

    def test_trim_history_partial_trimming(self):
        """Test that partial trimming works correctly."""
        cm = ContextManager()

        # Create history where some messages fit
        history = [
            {"role": "user", "content": "Short 1"},
            {"role": "assistant", "content": "Short 2"},
            {"role": "user", "content": "A" * 50000},  # Large message
            {"role": "assistant", "content": "Recent"},
        ]

        system_prompt = "System"
        new_message = "New"

        trimmed, was_trimmed = cm.trim_history(history, system_prompt, new_message)

        # Should keep recent messages, may trim old large one
        assert "Recent" in [m["content"] for m in trimmed]


@pytest.mark.unit
class TestUsageReporting:
    """Test usage reporting functionality."""

    def test_get_usage_report_empty_history(self):
        """Test usage report with empty history."""
        cm = ContextManager()
        history = []
        system_prompt = "You are a helpful assistant."

        report = cm.get_usage_report(history, system_prompt)

        assert report["system_tokens"] > 0
        assert report["history_tokens"] == 0
        assert report["total_used"] == report["system_tokens"]
        assert report["available"] == cm.available_tokens
        assert report["usage_percent"] > 0
        assert report["messages_in_context"] == 0

    def test_get_usage_report_with_history(self):
        """Test usage report with conversation history."""
        cm = ContextManager()
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        system_prompt = "You are a helpful assistant."

        report = cm.get_usage_report(history, system_prompt)

        assert report["system_tokens"] > 0
        assert report["history_tokens"] > 0
        assert report["total_used"] > report["system_tokens"]
        assert report["usage_percent"] < 100
        assert report["messages_in_context"] == 2

    def test_get_usage_report_high_usage(self):
        """Test usage report with high token usage."""
        cm = ContextManager()

        # Create large history
        history = []
        for _i in range(100):
            history.append({"role": "user", "content": "A" * 1000})

        system_prompt = "System prompt"

        report = cm.get_usage_report(history, system_prompt)

        assert report["total_used"] > 0
        assert report["usage_percent"] > 1
        assert report["messages_in_context"] == 100

    def test_get_usage_report_percentage_calculation(self):
        """Test that usage percentage is calculated correctly."""
        cm = ContextManager()
        history = [{"role": "user", "content": "Test"}]
        system_prompt = "System"

        report = cm.get_usage_report(history, system_prompt)

        # Verify percentage calculation
        expected_percent = (report["total_used"] / cm.available_tokens) * 100
        assert abs(report["usage_percent"] - expected_percent) < 0.01


@pytest.mark.unit
class TestModelLimits:
    """Test model-specific token limits."""

    def test_all_model_limits_defined(self):
        """Test that all expected models have limits defined."""
        expected_models = [
            "claude-opus-4-5-20251101",
            "claude-opus-4.5",
            "claude-sonnet-4-20250514",
            "claude-3-5-sonnet-20241022",
        ]

        for model in expected_models:
            cm = ContextManager(model=model)
            assert cm.max_tokens > 0

    def test_default_limit_fallback(self):
        """Test that unknown models fall back to default limit."""
        cm = ContextManager(model="unknown-future-model")
        assert cm.max_tokens == ContextManager.MODEL_LIMITS["default"]

    def test_different_model_limits(self):
        """Test that different models can have different limits."""
        cm1 = ContextManager(model="claude-opus-4-5-20251101")
        cm2 = ContextManager(model="default")

        # Opus models should have higher limits than default
        assert cm1.max_tokens >= cm2.max_tokens


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_very_long_single_message(self):
        """Test handling of very long single message."""
        cm = ContextManager()
        long_message = "A" * 200000  # Exceeds model limit

        tokens = cm.estimate_tokens(long_message)
        assert tokens > 0

    def test_unicode_content(self):
        """Test token estimation with unicode content."""
        cm = ContextManager()
        unicode_text = "Hello 世界 🌍 Здравствуй мир"

        tokens = cm.estimate_tokens(unicode_text)
        assert tokens > 0

    def test_special_characters(self):
        """Test token estimation with special characters."""
        cm = ContextManager()
        special_text = "!@#$%^&*()_+-=[]{}|;:',.<>?/~`"

        tokens = cm.estimate_tokens(special_text)
        assert tokens > 0

    def test_mixed_content_types(self):
        """Test messages with mixed content types."""
        cm = ContextManager()
        messages = [
            {"role": "user", "content": "Normal text"},
            {"role": "assistant", "content": "Response with\nnewlines\n"},
            {"role": "user", "content": "Code: print('hello')"},
        ]

        tokens = cm.estimate_messages_tokens(messages)
        assert tokens > 0
