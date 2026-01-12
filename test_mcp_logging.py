"""
Tests for MCP Structured Logging Module.

Validates all logging functionality including:
- Structured logging with context
- Sensitive data sanitization
- Log level categorization
- Performance metrics logging
- Context managers
"""

import json
import logging
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from Tools.adapters.mcp_logging import (
    LogCategory,
    LogContext,
    LogLevel,
    MCPLogger,
    SensitiveDataSanitizer,
    configure_logging,
    get_mcp_logger,
    log_operation,
)


# ============================================================================
# Test LogContext
# ============================================================================


def test_log_context_defaults():
    """Test LogContext creates valid default context."""
    context = LogContext()

    assert context.correlation_id is not None
    assert len(context.correlation_id) == 36  # UUID4 format
    assert context.server_name is None
    assert context.tool_name is None
    assert context.session_id is None
    assert context.operation is None
    assert context.category is None
    assert isinstance(context.timestamp, datetime)
    assert context.duration_ms is None
    assert context.metadata == {}


def test_log_context_with_values():
    """Test LogContext with custom values."""
    context = LogContext(
        server_name="test-server",
        tool_name="test_tool",
        operation="call_tool",
        category=LogCategory.TOOL_CALL,
        duration_ms=123.45,
        metadata={"key": "value"},
    )

    assert context.server_name == "test-server"
    assert context.tool_name == "test_tool"
    assert context.operation == "call_tool"
    assert context.category == LogCategory.TOOL_CALL
    assert context.duration_ms == 123.45
    assert context.metadata == {"key": "value"}


def test_log_context_to_dict():
    """Test LogContext serialization to dict."""
    context = LogContext(
        server_name="test-server",
        tool_name="test_tool",
        operation="call_tool",
        category=LogCategory.TOOL_CALL,
        duration_ms=123.45,
        metadata={"key": "value"},
    )

    data = context.to_dict()

    assert "correlation_id" in data
    assert data["server_name"] == "test-server"
    assert data["tool_name"] == "test_tool"
    assert data["operation"] == "call_tool"
    assert data["category"] == "tool_call"
    assert data["duration_ms"] == 123.45
    assert data["metadata"] == {"key": "value"}
    assert "timestamp" in data


def test_log_context_copy_with():
    """Test LogContext copy with updated fields."""
    context = LogContext(server_name="server1", tool_name="tool1")

    copied = context.copy_with(server_name="server2", operation="test_op")

    assert copied.server_name == "server2"
    assert copied.tool_name == "tool1"  # Unchanged
    assert copied.operation == "test_op"
    assert copied.correlation_id == context.correlation_id  # Same correlation


# ============================================================================
# Test SensitiveDataSanitizer
# ============================================================================


def test_sanitize_dict_with_password():
    """Test sanitization of password in dict."""
    data = {
        "username": "user",
        "password": "secret123",
        "other": "value",
    }

    sanitized = SensitiveDataSanitizer.sanitize_dict(data)

    assert sanitized["username"] == "user"
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["other"] == "value"


def test_sanitize_dict_with_api_key():
    """Test sanitization of API key in dict."""
    data = {
        "api_key": "sk-1234567890abcdef",
        "api-key": "another-key",
        "apikey": "yet-another",
        "data": "normal",
    }

    sanitized = SensitiveDataSanitizer.sanitize_dict(data)

    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["api-key"] == "[REDACTED]"
    assert sanitized["apikey"] == "[REDACTED]"
    assert sanitized["data"] == "normal"


def test_sanitize_dict_nested():
    """Test sanitization of nested dicts."""
    data = {
        "config": {
            "api_key": "secret",
            "url": "https://api.example.com",
        },
        "credentials": {
            "password": "pass123",
        },
    }

    sanitized = SensitiveDataSanitizer.sanitize_dict(data)

    assert sanitized["config"]["api_key"] == "[REDACTED]"
    assert sanitized["config"]["url"] == "https://api.example.com"
    assert sanitized["credentials"]["password"] == "[REDACTED]"


def test_sanitize_list():
    """Test sanitization of lists."""
    data = [
        {"api_key": "secret1"},
        {"password": "secret2"},
        {"safe": "value"},
    ]

    sanitized = SensitiveDataSanitizer.sanitize_list(data)

    assert sanitized[0]["api_key"] == "[REDACTED]"
    assert sanitized[1]["password"] == "[REDACTED]"
    assert sanitized[2]["safe"] == "value"


def test_sanitize_string_with_patterns():
    """Test sanitization of strings with sensitive patterns."""
    text = "password=secret123 api_key=sk-1234567890abcdef token=bearer_xyz"

    sanitized = SensitiveDataSanitizer.sanitize_string(text)

    assert "secret123" not in sanitized
    assert "sk-1234567890abcdef" not in sanitized
    assert "bearer_xyz" not in sanitized
    assert "[REDACTED]" in sanitized


def test_sanitize_mixed_data():
    """Test sanitization of mixed data structures."""
    data = {
        "user": "john",
        "auth": {
            "token": "secret-token-123",
            "refresh": "refresh-token-456",
        },
        "servers": [
            {"name": "server1", "api_key": "key1"},
            {"name": "server2", "password": "pass2"},
        ],
    }

    sanitized = SensitiveDataSanitizer.sanitize(data)

    assert sanitized["user"] == "john"
    assert sanitized["auth"]["token"] == "[REDACTED]"
    assert sanitized["auth"]["refresh"] == "[REDACTED]"
    assert sanitized["servers"][0]["name"] == "server1"
    assert sanitized["servers"][0]["api_key"] == "[REDACTED]"
    assert sanitized["servers"][1]["password"] == "[REDACTED]"


# ============================================================================
# Test MCPLogger
# ============================================================================


@pytest.fixture
def mcp_logger():
    """Create MCPLogger for testing."""
    return MCPLogger(name="test", enable_sanitization=True, enable_json=False)


@pytest.fixture
def mock_logger():
    """Create mock logger to capture calls."""
    return MagicMock()


def test_mcp_logger_initialization():
    """Test MCPLogger initialization."""
    logger = MCPLogger(name="test", enable_sanitization=True, enable_json=False)

    assert logger.logger.name == "test"
    assert logger.enable_sanitization is True
    assert logger.enable_json is False
    assert isinstance(logger.default_context, LogContext)


def test_debug_protocol(mcp_logger, mock_logger):
    """Test protocol message logging at DEBUG level."""
    mcp_logger.logger = mock_logger

    protocol_data = {
        "method": "initialize",
        "params": {"protocol_version": "1.0"},
    }

    mcp_logger.debug_protocol(
        "MCP initialize request",
        protocol_data=protocol_data,
        context=LogContext(server_name="test-server"),
    )

    assert mock_logger.debug.called
    call_args = mock_logger.debug.call_args
    assert "MCP initialize request" in call_args[0][0]
    assert "test-server" in call_args[0][0]


def test_info_connection(mcp_logger, mock_logger):
    """Test connection lifecycle logging at INFO level."""
    mcp_logger.logger = mock_logger

    mcp_logger.info_connection(
        "Connected to MCP server",
        context=LogContext(server_name="workos-mcp"),
        transport="stdio",
    )

    assert mock_logger.info.called
    call_args = mock_logger.info.call_args
    assert "Connected to MCP server" in call_args[0][0]
    assert "workos-mcp" in call_args[0][0]


def test_warn_retry(mcp_logger, mock_logger):
    """Test retry logging at WARNING level."""
    mcp_logger.logger = mock_logger

    error = Exception("Connection timeout")
    mcp_logger.warn_retry(
        "Retrying MCP operation",
        attempt=2,
        max_attempts=3,
        error=error,
        context=LogContext(server_name="test-server"),
    )

    assert mock_logger.warning.called
    call_args = mock_logger.warning.call_args
    assert "Retrying MCP operation" in call_args[0][0]


def test_warn_degradation(mcp_logger, mock_logger):
    """Test degradation logging at WARNING level."""
    mcp_logger.logger = mock_logger

    mcp_logger.warn_degradation(
        "Server performance degraded",
        metric_name="latency_ms",
        current_value=1500.0,
        threshold=1000.0,
        context=LogContext(server_name="slow-server"),
    )

    assert mock_logger.warning.called
    call_args = mock_logger.warning.call_args
    assert "Server performance degraded" in call_args[0][0]


def test_error_with_context(mcp_logger, mock_logger):
    """Test error logging with full context."""
    mcp_logger.logger = mock_logger

    error = ValueError("Invalid argument")
    mcp_logger.error_with_context(
        "Tool call failed",
        error=error,
        context=LogContext(tool_name="get_tasks"),
    )

    assert mock_logger.error.called
    call_args = mock_logger.error.call_args
    assert "Tool call failed" in call_args[0][0]
    assert call_args[1]["exc_info"] == error


def test_info_tool_call(mcp_logger, mock_logger):
    """Test tool call logging at INFO level."""
    mcp_logger.logger = mock_logger

    arguments = {"status": "active", "limit": 10}
    mcp_logger.info_tool_call(
        tool_name="get_tasks",
        arguments=arguments,
        success=True,
        duration_ms=123.45,
        context=LogContext(server_name="workos-mcp"),
    )

    assert mock_logger.info.called
    call_args = mock_logger.info.call_args
    assert "get_tasks" in call_args[0][0]
    assert "succeeded" in call_args[0][0]
    assert "123.45ms" in call_args[0][0]


def test_debug_cache(mcp_logger, mock_logger):
    """Test cache operation logging at DEBUG level."""
    mcp_logger.logger = mock_logger

    mcp_logger.debug_cache(
        operation="get",
        cache_key="get_tasks:status=active",
        hit=True,
        context=LogContext(server_name="workos-mcp"),
    )

    assert mock_logger.debug.called
    call_args = mock_logger.debug.call_args
    assert "Cache get" in call_args[0][0]
    assert "HIT" in call_args[0][0]


def test_info_metrics(mcp_logger, mock_logger):
    """Test metrics logging at INFO level."""
    mcp_logger.logger = mock_logger

    metrics = {
        "avg_latency_ms": 150.5,
        "success_rate": 0.95,
        "total_requests": 1000,
    }

    mcp_logger.info_metrics(
        metrics=metrics,
        context=LogContext(server_name="test-server"),
    )

    assert mock_logger.info.called
    call_args = mock_logger.info.call_args
    assert "Performance metrics" in call_args[0][0]


def test_sanitization_enabled(mcp_logger, mock_logger):
    """Test that sanitization works when enabled."""
    mcp_logger.logger = mock_logger
    mcp_logger.enable_sanitization = True

    mcp_logger.info(
        "Test message",
        context=LogContext(),
        password="secret123",
        api_key="sk-abcdef",
    )

    assert mock_logger.info.called
    call_args = mock_logger.info.call_args
    extra_data = call_args[1]["extra"]

    # Sensitive data should be redacted
    assert extra_data["extra"]["password"] == "[REDACTED]"
    assert extra_data["extra"]["api_key"] == "[REDACTED]"


def test_json_formatting():
    """Test JSON log formatting."""
    logger = MCPLogger(name="test", enable_json=True)

    with patch.object(logger.logger, 'info') as mock_info:
        logger.info("Test message", context=LogContext(server_name="test"))

        # Should have been called with JSON string
        assert mock_info.called
        message = mock_info.call_args[0][0]

        # Should be valid JSON
        parsed = json.loads(message)
        assert parsed["message"] == "Test message"
        assert "correlation_id" in parsed
        assert parsed["server_name"] == "test"


# ============================================================================
# Test log_operation Context Manager
# ============================================================================


def test_log_operation_success(mcp_logger, mock_logger):
    """Test log_operation context manager with successful operation."""
    mcp_logger.logger = mock_logger

    with log_operation(mcp_logger, "test_operation") as ctx:
        assert ctx.operation == "test_operation"
        assert ctx.correlation_id is not None

    # Should log start and completion
    assert mock_logger.debug.call_count == 2
    calls = [call[0][0] for call in mock_logger.debug.call_args_list]
    assert any("Starting operation" in call for call in calls)
    assert any("Operation completed" in call for call in calls)


def test_log_operation_error(mcp_logger, mock_logger):
    """Test log_operation context manager with error."""
    mcp_logger.logger = mock_logger

    with pytest.raises(ValueError):
        with log_operation(mcp_logger, "test_operation") as ctx:
            raise ValueError("Test error")

    # Should log start and error
    assert mock_logger.debug.call_count == 1  # Start
    assert mock_logger.error.call_count == 1  # Error

    error_call = mock_logger.error.call_args[0][0]
    assert "Operation failed" in error_call


# ============================================================================
# Test Convenience Functions
# ============================================================================


def test_get_mcp_logger():
    """Test get_mcp_logger convenience function."""
    logger = get_mcp_logger(name="test", enable_sanitization=True, enable_json=False)

    assert isinstance(logger, MCPLogger)
    assert logger.logger.name == "test"
    assert logger.enable_sanitization is True
    assert logger.enable_json is False


def test_configure_logging():
    """Test configure_logging function."""
    # Should not raise any errors
    configure_logging(level="DEBUG", enable_json=False)
    configure_logging(level="INFO", enable_json=True)

    # Verify logger level is set
    test_logger = logging.getLogger("mcp")
    # Level should be set (exact value depends on last call)
    assert test_logger.level in [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR]


# ============================================================================
# Integration Tests
# ============================================================================


def test_full_workflow():
    """Test a complete logging workflow."""
    logger = get_mcp_logger(name="integration_test", enable_sanitization=True)

    context = LogContext(
        server_name="test-server",
        tool_name="test_tool",
        category=LogCategory.TOOL_CALL,
    )

    with patch.object(logger.logger, 'info') as mock_info:
        # Log a tool call
        logger.info_tool_call(
            tool_name="get_tasks",
            arguments={"status": "active", "api_key": "secret"},
            success=True,
            duration_ms=123.45,
            context=context,
        )

        assert mock_info.called
        call_args = mock_info.call_args

        # Verify message
        message = call_args[0][0]
        assert "get_tasks" in message
        assert "succeeded" in message

        # Verify sanitization
        extra = call_args[1]["extra"]["extra"]
        assert extra["arguments"]["status"] == "active"
        assert extra["arguments"]["api_key"] == "[REDACTED]"


def test_context_propagation():
    """Test that context propagates through log operations."""
    logger = get_mcp_logger(name="context_test")

    base_context = LogContext(
        server_name="test-server",
        session_id="session-123",
    )

    with patch.object(logger.logger, 'debug') as mock_debug:
        with log_operation(logger, "parent_operation", context=base_context) as ctx:
            # Child operation should inherit context
            logger.debug("Child log", context=ctx.copy_with(operation="child_op"))

        # Verify context in logs
        assert mock_debug.call_count >= 2  # Start and child log

        # All calls should have same session_id
        for call in mock_debug.call_args_list:
            extra = call[1]["extra"]["extra"]
            if "session_id" in extra:
                assert extra["session_id"] == "session-123"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
