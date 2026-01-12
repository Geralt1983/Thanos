"""
MCP Error Handling.

Provides a comprehensive exception hierarchy for MCP operations,
enabling detailed error classification and graceful degradation strategies.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class MCPError(Exception):
    """
    Base exception for all MCP-related errors.

    All MCP exceptions inherit from this base class, allowing
    for catch-all error handling when needed.

    Attributes:
        message: Human-readable error description
        context: Additional context about the error
        server_name: Name of the MCP server (if applicable)
        retryable: Whether the operation can be retried
    """

    def __init__(
        self,
        message: str,
        context: Optional[dict[str, Any]] = None,
        server_name: Optional[str] = None,
        retryable: bool = False,
    ):
        """
        Initialize MCP error.

        Args:
            message: Error description
            context: Additional error context
            server_name: Server name where error occurred
            retryable: Whether operation can be retried
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.server_name = server_name
        self.retryable = retryable

    def __str__(self) -> str:
        """Return formatted error string."""
        parts = [self.message]
        if self.server_name:
            parts.append(f"(server: {self.server_name})")
        if self.context:
            parts.append(f"Context: {self.context}")
        return " ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert error to dictionary for logging/serialization.

        Returns:
            Dictionary with error details
        """
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "context": self.context,
            "server_name": self.server_name,
            "retryable": self.retryable,
        }


# Connection and Transport Errors


class MCPConnectionError(MCPError):
    """
    Error establishing or maintaining connection to MCP server.

    This error indicates problems with the underlying transport layer,
    such as network issues, subprocess failures, or protocol errors.
    Generally retryable with backoff.
    """

    def __init__(
        self,
        message: str,
        context: Optional[dict[str, Any]] = None,
        server_name: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            context=context,
            server_name=server_name,
            retryable=True,  # Connection errors are generally retryable
        )


class MCPTransportError(MCPError):
    """
    Transport-layer specific error.

    Indicates issues with the transport mechanism itself (stdio, SSE, HTTP).
    May or may not be retryable depending on the specific error.
    """

    def __init__(
        self,
        message: str,
        transport_type: str,
        context: Optional[dict[str, Any]] = None,
        server_name: Optional[str] = None,
        retryable: bool = True,
    ):
        context = context or {}
        context["transport_type"] = transport_type
        super().__init__(
            message=message,
            context=context,
            server_name=server_name,
            retryable=retryable,
        )


class MCPTimeoutError(MCPConnectionError):
    """
    Operation timed out.

    The MCP server didn't respond within the expected timeframe.
    Usually retryable with exponential backoff.
    """

    def __init__(
        self,
        message: str,
        timeout_seconds: float,
        context: Optional[dict[str, Any]] = None,
        server_name: Optional[str] = None,
    ):
        context = context or {}
        context["timeout_seconds"] = timeout_seconds
        super().__init__(
            message=message,
            context=context,
            server_name=server_name,
        )


# Protocol and Communication Errors


class MCPProtocolError(MCPError):
    """
    MCP protocol violation or communication error.

    Indicates that the server sent malformed responses or violated
    the MCP protocol specification. May indicate server bugs.
    Generally not retryable without server fixes.
    """

    def __init__(
        self,
        message: str,
        context: Optional[dict[str, Any]] = None,
        server_name: Optional[str] = None,
        retryable: bool = False,
    ):
        super().__init__(
            message=message,
            context=context,
            server_name=server_name,
            retryable=retryable,
        )


class MCPInitializationError(MCPProtocolError):
    """
    Error during MCP session initialization.

    Failed to establish session, negotiate capabilities, or complete
    the initialization handshake. May indicate configuration issues.
    """

    pass


class MCPCapabilityError(MCPProtocolError):
    """
    Server lacks required capability.

    The server doesn't support a capability that the client requires
    for the requested operation. Not retryable without capability support.
    """

    def __init__(
        self,
        message: str,
        capability: str,
        context: Optional[dict[str, Any]] = None,
        server_name: Optional[str] = None,
    ):
        context = context or {}
        context["missing_capability"] = capability
        super().__init__(
            message=message,
            context=context,
            server_name=server_name,
            retryable=False,  # Can't retry if capability is missing
        )


# Tool Execution Errors


class MCPToolError(MCPError):
    """
    Error executing a tool on the MCP server.

    Base class for tool-related errors. Specific tool execution
    failures should provide detailed context about the failure.
    """

    def __init__(
        self,
        message: str,
        tool_name: str,
        context: Optional[dict[str, Any]] = None,
        server_name: Optional[str] = None,
        retryable: bool = False,
    ):
        context = context or {}
        context["tool_name"] = tool_name
        super().__init__(
            message=message,
            context=context,
            server_name=server_name,
            retryable=retryable,
        )


class MCPToolNotFoundError(MCPToolError):
    """
    Requested tool doesn't exist on the server.

    The tool name is invalid or the server doesn't expose this tool.
    Not retryable unless tool list is refreshed.
    """

    def __init__(
        self,
        tool_name: str,
        available_tools: Optional[list[str]] = None,
        server_name: Optional[str] = None,
    ):
        context = {}
        if available_tools:
            context["available_tools"] = available_tools

        super().__init__(
            message=f"Tool '{tool_name}' not found on server",
            tool_name=tool_name,
            context=context,
            server_name=server_name,
            retryable=False,
        )


class MCPToolExecutionError(MCPToolError):
    """
    Tool execution failed on the server.

    The tool ran but returned an error or threw an exception.
    May be retryable depending on the specific error.
    """

    def __init__(
        self,
        tool_name: str,
        error_message: str,
        context: Optional[dict[str, Any]] = None,
        server_name: Optional[str] = None,
        retryable: bool = True,
    ):
        super().__init__(
            message=f"Tool '{tool_name}' execution failed: {error_message}",
            tool_name=tool_name,
            context=context,
            server_name=server_name,
            retryable=retryable,
        )


class MCPToolValidationError(MCPToolError):
    """
    Tool arguments failed validation.

    Arguments provided don't match the tool's schema or requirements.
    Not retryable without fixing the arguments.
    """

    def __init__(
        self,
        tool_name: str,
        validation_error: str,
        provided_arguments: Optional[dict[str, Any]] = None,
        server_name: Optional[str] = None,
    ):
        context = {"validation_error": validation_error}
        if provided_arguments:
            context["provided_arguments"] = provided_arguments

        super().__init__(
            message=f"Tool '{tool_name}' argument validation failed: {validation_error}",
            tool_name=tool_name,
            context=context,
            server_name=server_name,
            retryable=False,
        )


# Configuration and Setup Errors


class MCPConfigurationError(MCPError):
    """
    Invalid or missing MCP configuration.

    Configuration file is malformed, missing required fields, or
    contains invalid values. Not retryable without fixing config.
    """

    def __init__(
        self,
        message: str,
        config_path: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
        server_name: Optional[str] = None,
    ):
        context = context or {}
        if config_path:
            context["config_path"] = config_path

        super().__init__(
            message=message,
            context=context,
            server_name=server_name,
            retryable=False,
        )


class MCPDiscoveryError(MCPError):
    """
    Server discovery failed.

    Unable to discover or load MCP server configurations.
    May indicate missing config files or permission issues.
    """

    def __init__(
        self,
        message: str,
        search_paths: Optional[list[str]] = None,
        context: Optional[dict[str, Any]] = None,
    ):
        context = context or {}
        if search_paths:
            context["search_paths"] = search_paths

        super().__init__(
            message=message,
            context=context,
            retryable=False,
        )


# Server Health and Availability Errors


class MCPServerUnavailableError(MCPError):
    """
    MCP server is unavailable or unhealthy.

    Server failed health checks or is not responding.
    May be retryable after waiting for server recovery.
    """

    def __init__(
        self,
        message: str,
        server_name: str,
        last_health_check: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ):
        context = context or {}
        if last_health_check:
            context["last_health_check"] = last_health_check

        super().__init__(
            message=message,
            context=context,
            server_name=server_name,
            retryable=True,
        )


class MCPCircuitBreakerError(MCPServerUnavailableError):
    """
    Circuit breaker is open due to repeated failures.

    Too many consecutive failures have occurred, and the circuit
    breaker is preventing additional requests to protect the system.
    Retryable after circuit breaker timeout.
    """

    def __init__(
        self,
        server_name: str,
        failure_count: int,
        timeout_seconds: float,
        context: Optional[dict[str, Any]] = None,
    ):
        context = context or {}
        context.update(
            {
                "failure_count": failure_count,
                "timeout_seconds": timeout_seconds,
                "circuit_state": "open",
            }
        )

        super().__init__(
            message=f"Circuit breaker open for server '{server_name}' after {failure_count} failures",
            server_name=server_name,
            context=context,
        )


# Resource and Limit Errors


class MCPResourceError(MCPError):
    """
    Resource limit or availability error.

    Server or client ran out of resources (memory, connections, etc.).
    May be retryable after resources are freed.
    """

    def __init__(
        self,
        message: str,
        resource_type: str,
        context: Optional[dict[str, Any]] = None,
        server_name: Optional[str] = None,
        retryable: bool = True,
    ):
        context = context or {}
        context["resource_type"] = resource_type

        super().__init__(
            message=message,
            context=context,
            server_name=server_name,
            retryable=retryable,
        )


class MCPRateLimitError(MCPResourceError):
    """
    Rate limit exceeded.

    Too many requests in a given timeframe. Should be retried
    with exponential backoff.
    """

    def __init__(
        self,
        message: str,
        retry_after_seconds: Optional[float] = None,
        context: Optional[dict[str, Any]] = None,
        server_name: Optional[str] = None,
    ):
        context = context or {}
        if retry_after_seconds:
            context["retry_after_seconds"] = retry_after_seconds

        super().__init__(
            message=message,
            resource_type="rate_limit",
            context=context,
            server_name=server_name,
            retryable=True,
        )


# Utility Functions


def log_error_with_context(
    error: Exception,
    component: str = "mcp",
    additional_context: Optional[dict[str, Any]] = None,
) -> None:
    """
    Log an error with full context for debugging.

    Args:
        error: Exception to log
        component: Component name where error occurred
        additional_context: Extra context to include in log
    """
    context = additional_context or {}

    if isinstance(error, MCPError):
        # MCP errors already have rich context
        context.update(error.to_dict())
        logger.error(
            f"[{component}] MCP Error: {error.message}",
            extra={"mcp_context": context},
            exc_info=True,
        )
    else:
        # Generic exception
        logger.error(
            f"[{component}] Unexpected error: {error}",
            extra={"context": context},
            exc_info=True,
        )


def is_retryable_error(error: Exception) -> bool:
    """
    Check if an error is retryable.

    Args:
        error: Exception to check

    Returns:
        True if the error can be retried
    """
    if isinstance(error, MCPError):
        return error.retryable

    # Non-MCP errors - use heuristics
    # Network/connection errors are usually retryable
    error_type = type(error).__name__
    retryable_types = {
        "ConnectionError",
        "TimeoutError",
        "BrokenPipeError",
        "ConnectionResetError",
        "ConnectionAbortedError",
        "ConnectionRefusedError",
    }

    return error_type in retryable_types


def classify_error(error: Exception, server_name: Optional[str] = None) -> MCPError:
    """
    Convert a generic exception to an appropriate MCPError subclass.

    Args:
        error: Original exception
        server_name: Name of server where error occurred

    Returns:
        MCPError subclass appropriate for the error type
    """
    if isinstance(error, MCPError):
        # Already an MCP error
        return error

    error_message = str(error)
    error_type = type(error).__name__

    # Timeout errors
    if isinstance(error, TimeoutError) or "timeout" in error_message.lower():
        return MCPTimeoutError(
            message=error_message,
            timeout_seconds=0.0,  # Unknown timeout
            server_name=server_name,
        )

    # Connection errors
    if isinstance(error, (ConnectionError, BrokenPipeError)) or "connection" in error_message.lower():
        return MCPConnectionError(
            message=error_message,
            server_name=server_name,
        )

    # Generic MCP error
    return MCPError(
        message=f"{error_type}: {error_message}",
        server_name=server_name,
        retryable=is_retryable_error(error),
    )


# Error recovery strategies


class ErrorRecoveryStrategy:
    """
    Defines recovery strategies for different error types.

    Provides a centralized place to define fallback behaviors
    and recovery actions for various MCP errors.
    """

    @staticmethod
    def should_retry(error: Exception, attempt: int, max_attempts: int) -> bool:
        """
        Determine if an operation should be retried.

        Args:
            error: The error that occurred
            attempt: Current attempt number (1-indexed)
            max_attempts: Maximum retry attempts allowed

        Returns:
            True if operation should be retried
        """
        # Don't retry if we've exceeded max attempts
        if attempt >= max_attempts:
            return False

        # Check if error is retryable
        return is_retryable_error(error)

    @staticmethod
    def get_fallback_action(error: MCPError) -> str:
        """
        Get recommended fallback action for an error.

        Args:
            error: MCP error that occurred

        Returns:
            Human-readable fallback action recommendation
        """
        if isinstance(error, MCPToolNotFoundError):
            return "Refresh tool list and verify tool name"

        if isinstance(error, MCPCapabilityError):
            return "Use alternative approach or different server"

        if isinstance(error, MCPCircuitBreakerError):
            return f"Wait {error.context.get('timeout_seconds', 60)}s before retry"

        if isinstance(error, MCPConfigurationError):
            return "Check and fix configuration file"

        if isinstance(error, (MCPConnectionError, MCPTimeoutError)):
            return "Retry with exponential backoff"

        return "Check logs and retry if appropriate"
