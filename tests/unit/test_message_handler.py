#!/usr/bin/env python3
"""
Unit tests for MessageHandler

Tests message streaming, retry logic, error handling, and token tracking.
"""

from dataclasses import dataclass
from pathlib import Path
import sys
from unittest.mock import Mock, patch

import pytest


THANOS_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(THANOS_DIR))


# Create mock exception classes that behave like Anthropic exceptions
# The real Anthropic exceptions require response and body parameters
class MockRateLimitError(Exception):
    """Mock RateLimitError for testing."""

    def __init__(self, message="Rate limited"):
        super().__init__(message)
        self.status_code = 429


class MockAPIConnectionError(Exception):
    """Mock APIConnectionError for testing."""

    def __init__(self, message="Connection error"):
        super().__init__(message)


class MockAPIStatusError(Exception):
    """Mock APIStatusError for testing."""

    def __init__(self, message="API error", status_code=500):
        super().__init__(message)
        self.status_code = status_code


# Patch the anthropic imports in message_handler module
import Tools.message_handler as handler_module


handler_module.RateLimitError = MockRateLimitError
handler_module.APIConnectionError = MockAPIConnectionError
handler_module.APIStatusError = MockAPIStatusError

# Use the mock classes in tests
RateLimitError = MockRateLimitError
APIConnectionError = MockAPIConnectionError
APIStatusError = MockAPIStatusError

from Tools.message_handler import MessageHandler


@dataclass
class MockUsage:
    """Mock usage stats from API"""

    input_tokens: int
    output_tokens: int


@dataclass
class MockMessage:
    """Mock API message response"""

    usage: MockUsage


class MockStream:
    """Mock streaming response from API"""

    def __init__(self, chunks, final_message):
        self.text_stream = chunks
        self._final_message = final_message

    def get_final_message(self):
        return self._final_message

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class TestMessageHandler:
    """Test suite for MessageHandler"""

    @pytest.fixture
    def mock_client_factory(self):
        """Create mock client factory"""
        client = Mock()
        return lambda: client

    @pytest.fixture
    def mock_session_manager(self):
        """Create mock session manager"""
        return Mock()

    @pytest.fixture
    def mock_context_manager(self):
        """Create mock context manager"""
        return Mock()

    @pytest.fixture
    def mock_retry_middleware(self):
        """Create mock retry middleware"""
        middleware = Mock()
        # Default behavior: execute operation successfully
        middleware.execute_with_retry.side_effect = lambda operation, **kwargs: operation()
        return middleware

    @pytest.fixture
    def message_handler(
        self, mock_client_factory, mock_session_manager, mock_context_manager, mock_retry_middleware
    ):
        """Create MessageHandler instance with mocked dependencies"""
        return MessageHandler(
            client_factory=mock_client_factory,
            session_manager=mock_session_manager,
            context_manager=mock_context_manager,
            retry_middleware=mock_retry_middleware,
        )

    def test_successful_message_streaming(self, message_handler, mock_client_factory):
        """Test successful message streaming with token tracking"""
        # Setup mock client
        client = mock_client_factory()
        chunks = ["Hello", " ", "world", "!"]
        final_message = MockMessage(usage=MockUsage(input_tokens=10, output_tokens=5))
        mock_stream = MockStream(chunks, final_message)
        client.chat_stream.return_value = mock_stream

        # Test
        with patch("builtins.print"):  # Suppress output
            result = message_handler.handle_message(
                message="Test message",
                system_prompt="Test prompt",
                history=[],
                operation="test:op",
                agent_name="TestAgent",
            )

        # Verify
        assert result.success is True
        assert result.response == "Hello world!"
        assert result.input_tokens == 10
        assert result.output_tokens == 5
        assert result.error is None

    def test_rate_limit_error(self, message_handler, mock_retry_middleware):
        """Test rate limit error handling"""
        # Setup retry middleware to raise RateLimitError
        mock_retry_middleware.execute_with_retry.side_effect = RateLimitError("Rate limit")

        # Test
        with patch("builtins.print"):  # Suppress output
            result = message_handler.handle_message(
                message="Test message",
                system_prompt="Test prompt",
                history=[],
                operation="test:op",
                agent_name="TestAgent",
            )

        # Verify
        assert result.success is False
        assert result.response == ""
        assert result.input_tokens == 0
        assert result.output_tokens == 0
        assert "Rate limit" in result.error

    def test_connection_error(self, message_handler, mock_retry_middleware):
        """Test connection error handling"""
        # Setup retry middleware to raise APIConnectionError
        mock_retry_middleware.execute_with_retry.side_effect = APIConnectionError(
            "Connection failed"
        )

        # Test
        with patch("builtins.print"):  # Suppress output
            result = message_handler.handle_message(
                message="Test message",
                system_prompt="Test prompt",
                history=[],
                operation="test:op",
                agent_name="TestAgent",
            )

        # Verify
        assert result.success is False
        assert result.response == ""
        assert result.input_tokens == 0
        assert result.output_tokens == 0
        assert "network" in result.error.lower()

    def test_api_status_error_4xx(self, message_handler, mock_retry_middleware):
        """Test API status error (4xx) handling"""
        # Setup retry middleware to raise APIStatusError with 4xx status
        error = APIStatusError("Bad request", status_code=400)
        mock_retry_middleware.execute_with_retry.side_effect = error

        # Test
        with patch("builtins.print"):  # Suppress output
            result = message_handler.handle_message(
                message="Test message",
                system_prompt="Test prompt",
                history=[],
                operation="test:op",
                agent_name="TestAgent",
            )

        # Verify
        assert result.success is False
        assert result.response == ""
        assert "API error" in result.error

    def test_api_status_error_5xx(self, message_handler, mock_retry_middleware):
        """Test API status error (5xx) handling"""
        # Setup retry middleware to raise APIStatusError with 5xx status
        error = APIStatusError("Server error", status_code=500)
        mock_retry_middleware.execute_with_retry.side_effect = error

        # Test
        with patch("builtins.print"):  # Suppress output
            result = message_handler.handle_message(
                message="Test message",
                system_prompt="Test prompt",
                history=[],
                operation="test:op",
                agent_name="TestAgent",
            )

        # Verify
        assert result.success is False
        assert result.response == ""
        assert "unavailable" in result.error.lower()

    def test_unexpected_error(self, message_handler, mock_retry_middleware):
        """Test unexpected error handling"""
        # Setup retry middleware to raise unexpected error
        mock_retry_middleware.execute_with_retry.side_effect = ValueError("Unexpected error")

        # Test
        with patch("builtins.print"):  # Suppress output
            result = message_handler.handle_message(
                message="Test message",
                system_prompt="Test prompt",
                history=[],
                operation="test:op",
                agent_name="TestAgent",
            )

        # Verify
        assert result.success is False
        assert result.response == ""
        assert "Unexpected" in result.error

    def test_retry_callback_invoked(
        self, message_handler, mock_retry_middleware, mock_client_factory
    ):
        """Test that retry callback is passed to middleware"""
        # Setup mock client to succeed
        client = mock_client_factory()
        chunks = ["Test"]
        final_message = MockMessage(usage=MockUsage(input_tokens=5, output_tokens=3))
        mock_stream = MockStream(chunks, final_message)
        client.chat_stream.return_value = mock_stream

        # Test
        with patch("builtins.print"):  # Suppress output
            result = message_handler.handle_message(
                message="Test message",
                system_prompt="Test prompt",
                history=[],
                operation="test:op",
                agent_name="TestAgent",
            )

        # Verify retry middleware was called with callback
        mock_retry_middleware.execute_with_retry.assert_called_once()
        call_kwargs = mock_retry_middleware.execute_with_retry.call_args.kwargs
        assert "on_retry" in call_kwargs
        assert callable(call_kwargs["on_retry"])
        assert "retriable_errors" in call_kwargs

    def test_lazy_client_initialization(self, message_handler, mock_client_factory):
        """Test that client is lazily initialized"""
        # Client should not be initialized yet
        assert message_handler._client is None

        # Setup mock client
        client = mock_client_factory()
        chunks = ["Test"]
        final_message = MockMessage(usage=MockUsage(input_tokens=5, output_tokens=3))
        mock_stream = MockStream(chunks, final_message)
        client.chat_stream.return_value = mock_stream

        # Handle message (should initialize client)
        with patch("builtins.print"):  # Suppress output
            result = message_handler.handle_message(
                message="Test message",
                system_prompt="Test prompt",
                history=[],
                operation="test:op",
                agent_name="TestAgent",
            )

        # Client should now be initialized
        assert message_handler._client is not None
        assert result.success is True

    def test_empty_response(self, message_handler, mock_client_factory):
        """Test handling of empty response"""
        # Setup mock client with empty response
        client = mock_client_factory()
        chunks = []
        final_message = MockMessage(usage=MockUsage(input_tokens=5, output_tokens=0))
        mock_stream = MockStream(chunks, final_message)
        client.chat_stream.return_value = mock_stream

        # Test
        with patch("builtins.print"):  # Suppress output
            result = message_handler.handle_message(
                message="Test message",
                system_prompt="Test prompt",
                history=[],
                operation="test:op",
                agent_name="TestAgent",
            )

        # Verify
        assert result.success is True
        assert result.response == ""
        assert result.input_tokens == 5
        assert result.output_tokens == 0

    def test_long_streaming_response(self, message_handler, mock_client_factory):
        """Test streaming of long response"""
        # Setup mock client with many chunks
        client = mock_client_factory()
        chunks = ["Chunk"] * 100
        final_message = MockMessage(usage=MockUsage(input_tokens=50, output_tokens=200))
        mock_stream = MockStream(chunks, final_message)
        client.chat_stream.return_value = mock_stream

        # Test
        with patch("builtins.print"):  # Suppress output
            result = message_handler.handle_message(
                message="Test message",
                system_prompt="Test prompt",
                history=[],
                operation="test:op",
                agent_name="TestAgent",
            )

        # Verify
        assert result.success is True
        assert result.response == "Chunk" * 100
        assert result.input_tokens == 50
        assert result.output_tokens == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
