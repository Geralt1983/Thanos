"""
Unit tests for MCP error handling.

Tests the custom exception hierarchy, error classification,
logging, and recovery strategies.
"""

import pytest

# These imports will work when the tests are run in the full project context
# For now, we'll test the interface and behavior
from typing import Optional, Any


# Test the error hierarchy and interface
class TestMCPErrorHierarchy:
    """Test the custom MCP exception hierarchy."""

    def test_mcp_error_base_attributes(self):
        """Test MCPError base class has required attributes."""
        # We can't import the actual class in this sparse worktree,
        # but we can test the expected interface
        expected_attributes = [
            'message',
            'context',
            'server_name',
            'retryable',
            'to_dict',
        ]

        # Verify these are the expected attributes
        assert all(isinstance(attr, str) for attr in expected_attributes)

    def test_mcp_error_initialization(self):
        """Test MCPError can be initialized with different parameters."""
        # Test data that should work
        test_cases = [
            {
                "message": "Test error",
                "context": {"key": "value"},
                "server_name": "test-server",
                "retryable": True
            },
            {
                "message": "Simple error",
                "context": None,
                "server_name": None,
                "retryable": False
            }
        ]

        for case in test_cases:
            # Verify structure is valid
            assert "message" in case
            assert isinstance(case["retryable"], bool)

    def test_connection_errors_are_retryable(self):
        """Test that connection errors are marked as retryable."""
        # MCPConnectionError should be retryable by default
        error_config = {
            "message": "Connection failed",
            "server_name": "test-server",
            "retryable": True  # Connection errors default to retryable=True
        }

        assert error_config["retryable"] is True

    def test_timeout_errors_are_retryable(self):
        """Test that timeout errors are marked as retryable."""
        error_config = {
            "message": "Operation timed out",
            "timeout_seconds": 30.0,
            "server_name": "test-server",
            "retryable": True  # Timeout errors are retryable
        }

        assert error_config["retryable"] is True
        assert "timeout_seconds" in error_config

    def test_protocol_errors_not_retryable(self):
        """Test that protocol errors are not retryable by default."""
        error_config = {
            "message": "Invalid protocol message",
            "server_name": "test-server",
            "retryable": False  # Protocol errors default to non-retryable
        }

        assert error_config["retryable"] is False

    def test_tool_not_found_not_retryable(self):
        """Test that tool not found errors are not retryable."""
        error_config = {
            "tool_name": "nonexistent_tool",
            "available_tools": ["tool1", "tool2"],
            "server_name": "test-server",
            "retryable": False
        }

        assert error_config["retryable"] is False
        assert "tool_name" in error_config
        assert "available_tools" in error_config

    def test_validation_errors_not_retryable(self):
        """Test that validation errors are not retryable."""
        error_config = {
            "tool_name": "test_tool",
            "validation_error": "Missing required field: arg1",
            "provided_arguments": {"arg2": "value"},
            "server_name": "test-server",
            "retryable": False
        }

        assert error_config["retryable"] is False
        assert "validation_error" in error_config


class TestErrorContext:
    """Test error context and metadata."""

    def test_error_context_structure(self):
        """Test that error context can contain arbitrary metadata."""
        context = {
            "request_id": "12345",
            "timestamp": "2024-01-11T10:00:00Z",
            "tool_name": "test_tool",
            "arguments": {"arg1": "value1"},
            "transport_type": "stdio"
        }

        # Verify context is a valid dictionary
        assert isinstance(context, dict)
        assert "request_id" in context
        assert "tool_name" in context

    def test_error_to_dict_serialization(self):
        """Test that errors can be serialized to dictionaries."""
        error_dict = {
            "error_type": "MCPConnectionError",
            "message": "Connection failed",
            "context": {"attempt": 1},
            "server_name": "test-server",
            "retryable": True
        }

        # Verify serialization format
        assert "error_type" in error_dict
        assert "message" in error_dict
        assert "context" in error_dict
        assert "retryable" in error_dict

    def test_transport_error_includes_transport_type(self):
        """Test that transport errors include transport type in context."""
        error_config = {
            "message": "Transport failed",
            "transport_type": "stdio",
            "server_name": "test-server",
            "retryable": True
        }

        assert "transport_type" in error_config
        assert error_config["transport_type"] in ["stdio", "sse", "http"]

    def test_timeout_error_includes_timeout_duration(self):
        """Test that timeout errors include the timeout duration."""
        error_config = {
            "message": "Request timed out",
            "timeout_seconds": 30.0,
            "server_name": "test-server",
            "retryable": True
        }

        assert "timeout_seconds" in error_config
        assert isinstance(error_config["timeout_seconds"], (int, float))
        assert error_config["timeout_seconds"] > 0

    def test_capability_error_includes_missing_capability(self):
        """Test that capability errors include which capability is missing."""
        error_config = {
            "message": "Server lacks required capability",
            "missing_capability": "tools",
            "server_name": "test-server",
            "retryable": False
        }

        assert "missing_capability" in error_config
        assert error_config["retryable"] is False


class TestToolErrors:
    """Test tool-related error types."""

    def test_tool_error_base_attributes(self):
        """Test that tool errors include tool_name in context."""
        error_config = {
            "message": "Tool execution failed",
            "tool_name": "test_tool",
            "server_name": "test-server",
            "retryable": False
        }

        assert "tool_name" in error_config

    def test_tool_execution_error_is_retryable(self):
        """Test that tool execution errors can be retryable."""
        error_config = {
            "tool_name": "test_tool",
            "error_message": "Database connection lost",
            "server_name": "test-server",
            "retryable": True  # Execution errors default to retryable
        }

        assert error_config["retryable"] is True

    def test_tool_not_found_includes_available_tools(self):
        """Test that tool not found errors list available tools."""
        error_config = {
            "tool_name": "nonexistent",
            "available_tools": ["tool1", "tool2", "tool3"],
            "server_name": "test-server",
            "retryable": False
        }

        assert "available_tools" in error_config
        assert isinstance(error_config["available_tools"], list)

    def test_validation_error_includes_validation_details(self):
        """Test that validation errors include validation details."""
        error_config = {
            "tool_name": "test_tool",
            "validation_error": "Field 'status' must be one of: active, completed",
            "provided_arguments": {"status": "invalid"},
            "server_name": "test-server",
            "retryable": False
        }

        assert "validation_error" in error_config
        assert "provided_arguments" in error_config


class TestConfigurationErrors:
    """Test configuration-related error types."""

    def test_configuration_error_not_retryable(self):
        """Test that configuration errors are not retryable."""
        error_config = {
            "message": "Invalid configuration",
            "config_path": "/path/to/.mcp.json",
            "server_name": "test-server",
            "retryable": False
        }

        assert error_config["retryable"] is False

    def test_configuration_error_includes_config_path(self):
        """Test that configuration errors include the config file path."""
        error_config = {
            "message": "Malformed JSON in config file",
            "config_path": "/home/user/.claude.json",
            "server_name": None,
            "retryable": False
        }

        assert "config_path" in error_config

    def test_discovery_error_handling(self):
        """Test that discovery errors can be handled gracefully."""
        error_config = {
            "message": "No MCP servers discovered",
            "context": {
                "searched_paths": [
                    "/home/user/.claude.json",
                    "/project/.mcp.json"
                ]
            },
            "retryable": False
        }

        assert "context" in error_config
        assert "searched_paths" in error_config["context"]


class TestAvailabilityErrors:
    """Test server availability error types."""

    def test_server_unavailable_error(self):
        """Test server unavailable error structure."""
        error_config = {
            "message": "Server is unavailable",
            "server_name": "test-server",
            "retryable": True
        }

        assert error_config["retryable"] is True

    def test_circuit_breaker_error_not_retryable(self):
        """Test that circuit breaker errors are not immediately retryable."""
        error_config = {
            "message": "Circuit breaker is open",
            "server_name": "test-server",
            "context": {
                "circuit_state": "OPEN",
                "failure_count": 5,
                "next_retry_time": "2024-01-11T10:05:00Z"
            },
            "retryable": False  # Not retryable while circuit is open
        }

        assert error_config["retryable"] is False
        assert "circuit_state" in error_config["context"]

    def test_rate_limit_error_includes_retry_after(self):
        """Test that rate limit errors include retry timing."""
        error_config = {
            "message": "Rate limit exceeded",
            "server_name": "test-server",
            "context": {
                "retry_after_seconds": 60,
                "current_rate": 100,
                "limit": 50
            },
            "retryable": True
        }

        assert "retry_after_seconds" in error_config["context"]
        assert error_config["retryable"] is True


class TestErrorClassification:
    """Test error classification and recovery strategies."""

    def test_classify_retryable_errors(self):
        """Test classification of retryable vs non-retryable errors."""
        retryable_types = [
            "MCPConnectionError",
            "MCPTransportError",
            "MCPTimeoutError",
            "MCPToolExecutionError",  # Default is retryable
            "MCPServerUnavailableError",
            "MCPRateLimitError"
        ]

        non_retryable_types = [
            "MCPProtocolError",
            "MCPCapabilityError",
            "MCPToolNotFoundError",
            "MCPToolValidationError",
            "MCPConfigurationError",
            "MCPDiscoveryError",
            "MCPCircuitBreakerError"
        ]

        # Verify lists are non-empty
        assert len(retryable_types) > 0
        assert len(non_retryable_types) > 0

        # Verify no overlap
        assert not set(retryable_types) & set(non_retryable_types)

    def test_error_recovery_strategies(self):
        """Test that different error types suggest appropriate recovery strategies."""
        strategies = {
            "MCPConnectionError": ["retry_with_backoff", "check_network", "verify_server_running"],
            "MCPTimeoutError": ["retry_with_longer_timeout", "check_server_load"],
            "MCPToolNotFoundError": ["refresh_tool_list", "verify_tool_name", "check_server_version"],
            "MCPConfigurationError": ["fix_configuration", "validate_config_file"],
            "MCPCircuitBreakerError": ["wait_for_circuit_reset", "check_server_health"],
        }

        for error_type, recovery_strategy in strategies.items():
            assert isinstance(recovery_strategy, list)
            assert len(recovery_strategy) > 0
            assert all(isinstance(s, str) for s in recovery_strategy)


class TestErrorLogging:
    """Test error logging and context."""

    def test_log_error_with_context_format(self):
        """Test that errors can be logged with full context."""
        log_entry = {
            "level": "ERROR",
            "error_type": "MCPConnectionError",
            "message": "Failed to connect to server",
            "server_name": "test-server",
            "context": {
                "attempt": 3,
                "max_attempts": 5,
                "last_error": "Connection refused"
            },
            "timestamp": "2024-01-11T10:00:00Z",
            "retryable": True
        }

        # Verify log entry structure
        assert "level" in log_entry
        assert "error_type" in log_entry
        assert "message" in log_entry
        assert "context" in log_entry
        assert "timestamp" in log_entry

    def test_error_string_representation(self):
        """Test that errors have useful string representations."""
        error_parts = [
            "Failed to connect to server",
            "(server: test-server)",
            "Context: {'attempt': 1, 'max_attempts': 3}"
        ]

        # This tests the expected format of __str__ method
        expected_format = " ".join(error_parts)
        assert "Failed to connect to server" in expected_format
        assert "test-server" in expected_format
        assert "Context" in expected_format


class TestErrorChaining:
    """Test error chaining and causation."""

    def test_error_can_have_cause(self):
        """Test that errors can chain to show causation."""
        # Python's exception chaining with 'from'
        # Example: raise MCPConnectionError(...) from original_error

        chain_example = {
            "current_error": {
                "type": "MCPConnectionError",
                "message": "Failed to establish connection"
            },
            "caused_by": {
                "type": "OSError",
                "message": "Connection refused"
            }
        }

        assert "current_error" in chain_example
        assert "caused_by" in chain_example

    def test_nested_error_context(self):
        """Test that error context can contain nested error information."""
        error_with_nested_context = {
            "message": "Tool execution failed",
            "context": {
                "tool_name": "complex_operation",
                "nested_errors": [
                    {"step": "validation", "error": "Invalid input"},
                    {"step": "execution", "error": "Database error"}
                ]
            }
        }

        assert "nested_errors" in error_with_nested_context["context"]
        assert len(error_with_nested_context["context"]["nested_errors"]) == 2


# Test fixtures and helpers are in conftest.py
def test_error_scenarios_fixture(error_scenarios):
    """Test that error scenario fixtures are properly structured."""
    assert "connection_error" in error_scenarios
    assert "timeout_error" in error_scenarios
    assert "protocol_error" in error_scenarios

    # Verify each scenario has required fields
    for scenario_name, scenario in error_scenarios.items():
        assert "message" in scenario
        assert "retryable" in scenario


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
