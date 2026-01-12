"""
MCP Structured Logging Module.

Provides comprehensive structured logging for all MCP operations with:
- Debug logs for all MCP protocol messages
- Info logs for connection lifecycle events
- Warning logs for retries and degradation
- Error logs with full context
- Log sanitization for sensitive data

This module implements best practices for production logging including:
- Contextual information in all log entries
- Automatic sanitization of secrets and credentials
- Performance metrics logging
- Correlation IDs for request tracking
- JSON-structured logging support
"""

from __future__ import annotations

import json
import logging
import re
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

# Default logger instance
logger = logging.getLogger(__name__)


class LogLevel(str, Enum):
    """
    Standard log levels for MCP operations.

    Maps to standard Python logging levels.
    """
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(str, Enum):
    """
    Categories for MCP log entries.

    Used for filtering and organizing logs by operation type.
    """
    PROTOCOL = "protocol"          # MCP protocol messages (initialize, list_tools, etc.)
    CONNECTION = "connection"      # Connection lifecycle (connect, disconnect, reconnect)
    TOOL_CALL = "tool_call"       # Tool invocations
    TRANSPORT = "transport"        # Transport layer operations
    CACHE = "cache"               # Caching operations
    HEALTH = "health"             # Health check operations
    RETRY = "retry"               # Retry and circuit breaker operations
    DEGRADATION = "degradation"   # Performance degradation events
    VALIDATION = "validation"     # Validation operations
    DISCOVERY = "discovery"       # Server discovery operations
    POOL = "pool"                 # Connection pooling operations
    LOADBALANCER = "loadbalancer" # Load balancing operations
    METRICS = "metrics"           # Performance metrics
    SECURITY = "security"         # Security-related events


@dataclass
class LogContext:
    """
    Context information included in all log entries.

    Provides rich metadata for debugging and tracing operations.
    """

    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    """Unique ID for correlating related log entries"""

    server_name: Optional[str] = None
    """Name of the MCP server"""

    tool_name: Optional[str] = None
    """Name of the tool being invoked"""

    session_id: Optional[str] = None
    """MCP session identifier"""

    operation: Optional[str] = None
    """Operation being performed (e.g., 'initialize', 'call_tool')"""

    category: Optional[LogCategory] = None
    """Log category for filtering"""

    timestamp: Optional[datetime] = field(default_factory=datetime.utcnow)
    """When the log entry was created"""

    duration_ms: Optional[float] = None
    """Duration of operation in milliseconds"""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata specific to the operation"""

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert context to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the context
        """
        result = {
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

        if self.server_name:
            result["server_name"] = self.server_name
        if self.tool_name:
            result["tool_name"] = self.tool_name
        if self.session_id:
            result["session_id"] = self.session_id
        if self.operation:
            result["operation"] = self.operation
        if self.category:
            result["category"] = self.category.value
        if self.duration_ms is not None:
            result["duration_ms"] = round(self.duration_ms, 2)
        if self.metadata:
            result["metadata"] = self.metadata

        return result

    def copy_with(self, **kwargs) -> LogContext:
        """
        Create a copy of this context with updated fields.

        Args:
            **kwargs: Fields to update

        Returns:
            New LogContext instance with updated fields
        """
        data = asdict(self)
        data.update(kwargs)
        return LogContext(**data)


class SensitiveDataSanitizer:
    """
    Sanitizes sensitive data from log messages and context.

    Prevents accidental logging of secrets, API keys, passwords, tokens,
    and other sensitive information.
    """

    # Patterns for sensitive data detection
    SENSITIVE_KEYS: Set[str] = {
        "password", "passwd", "pwd",
        "secret", "api_key", "apikey", "api-key",
        "token", "access_token", "refresh_token", "refresh", "bearer",
        "credential", "credentials",
        "authorization", "auth",
        "private_key", "private-key",
        "session_id", "sessionid",
        "cookie", "cookies",
        "connection_string", "database_url", "db_url",
    }

    # Regex patterns for sensitive data in strings
    SENSITIVE_PATTERNS: List[re.Pattern] = [
        re.compile(r'(password|passwd|pwd)\s*[:=]\s*[\'"]?([^\s\'"]+)', re.IGNORECASE),
        re.compile(r'(api[_-]?key|apikey)\s*[:=]\s*[\'"]?([^\s\'"]+)', re.IGNORECASE),
        re.compile(r'(token|bearer)\s*[:=]\s*[\'"]?([^\s\'"]+)', re.IGNORECASE),
        re.compile(r'(secret)\s*[:=]\s*[\'"]?([^\s\'"]+)', re.IGNORECASE),
        re.compile(r'(authorization)\s*:\s*[\'"]?([^\s\'"]+)', re.IGNORECASE),
        # Common secret formats
        re.compile(r'\b[a-zA-Z0-9]{32,}\b'),  # Long alphanumeric strings (potential keys)
        re.compile(r'\bsk-[a-zA-Z0-9]{32,}\b'),  # OpenAI-style keys
        re.compile(r'\bghp_[a-zA-Z0-9]{36}\b'),  # GitHub Personal Access Tokens
        re.compile(r'\bglpat-[a-zA-Z0-9_\-]{20,}\b'),  # GitLab tokens
    ]

    REDACTED = "[REDACTED]"

    @classmethod
    def sanitize_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize sensitive data from a dictionary.

        Args:
            data: Dictionary to sanitize

        Returns:
            Sanitized dictionary with sensitive values redacted
        """
        if not isinstance(data, dict):
            return data

        sanitized = {}
        for key, value in data.items():
            # Check if key is sensitive
            key_lower = key.lower().replace("-", "_").replace(" ", "_")
            is_sensitive_key = any(sensitive in key_lower for sensitive in cls.SENSITIVE_KEYS)

            if is_sensitive_key and isinstance(value, str):
                # Only redact string values for sensitive keys
                sanitized[key] = cls.REDACTED
            elif isinstance(value, dict):
                # Always recurse into dicts (even for sensitive keys)
                sanitized[key] = cls.sanitize_dict(value)
            elif isinstance(value, (list, tuple)):
                # Always recurse into lists
                sanitized[key] = cls.sanitize_list(value)
            elif isinstance(value, str):
                # Sanitize strings using pattern matching
                sanitized[key] = cls.sanitize_string(value)
            else:
                # Other types: keep as-is unless key is sensitive
                sanitized[key] = cls.REDACTED if is_sensitive_key else value

        return sanitized

    @classmethod
    def sanitize_list(cls, data: List[Any]) -> List[Any]:
        """
        Sanitize sensitive data from a list.

        Args:
            data: List to sanitize

        Returns:
            Sanitized list
        """
        if not isinstance(data, (list, tuple)):
            return data

        sanitized = []
        for item in data:
            if isinstance(item, dict):
                sanitized.append(cls.sanitize_dict(item))
            elif isinstance(item, (list, tuple)):
                sanitized.append(cls.sanitize_list(item))
            elif isinstance(item, str):
                sanitized.append(cls.sanitize_string(item))
            else:
                sanitized.append(item)

        return sanitized

    @classmethod
    def sanitize_string(cls, text: str) -> str:
        """
        Sanitize sensitive data from a string.

        Args:
            text: String to sanitize

        Returns:
            Sanitized string with sensitive patterns redacted
        """
        if not isinstance(text, str):
            return text

        # Apply regex patterns to redact sensitive data
        sanitized = text
        for pattern in cls.SENSITIVE_PATTERNS:
            sanitized = pattern.sub(lambda m: cls.REDACTED, sanitized)

        return sanitized

    @classmethod
    def sanitize(cls, data: Any) -> Any:
        """
        Sanitize sensitive data from any data structure.

        Args:
            data: Data to sanitize (dict, list, str, or other)

        Returns:
            Sanitized data
        """
        if isinstance(data, dict):
            return cls.sanitize_dict(data)
        elif isinstance(data, (list, tuple)):
            return cls.sanitize_list(data)
        elif isinstance(data, str):
            return cls.sanitize_string(data)
        else:
            return data


class MCPLogger:
    """
    Structured logger for MCP operations.

    Provides high-level logging methods with automatic context enrichment
    and sanitization.
    """

    def __init__(
        self,
        name: str = "mcp",
        enable_sanitization: bool = True,
        enable_json: bool = False,
        default_context: Optional[LogContext] = None,
    ):
        """
        Initialize MCP logger.

        Args:
            name: Logger name (usually module name)
            enable_sanitization: Whether to sanitize sensitive data
            enable_json: Whether to format logs as JSON
            default_context: Default context for all log entries
        """
        self.logger = logging.getLogger(name)
        self.enable_sanitization = enable_sanitization
        self.enable_json = enable_json
        self.default_context = default_context or LogContext()

    def _prepare_message(
        self,
        message: str,
        context: Optional[LogContext] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> tuple[str, Dict[str, Any]]:
        """
        Prepare log message with context and sanitization.

        Args:
            message: Log message
            context: Log context
            extra: Extra data to include

        Returns:
            Tuple of (formatted_message, extra_dict)
        """
        # Merge contexts
        log_context = self.default_context.copy_with()
        if context:
            for key, value in asdict(context).items():
                if value is not None:
                    setattr(log_context, key, value)

        # Prepare extra data
        extra_data = log_context.to_dict()
        if extra:
            sanitized_extra = SensitiveDataSanitizer.sanitize(extra) if self.enable_sanitization else extra
            extra_data.update(sanitized_extra)

        # Format message
        if self.enable_json:
            log_data = {
                "message": message,
                **extra_data,
            }
            formatted_message = json.dumps(log_data)
        else:
            # Add correlation ID to message for tracing
            formatted_message = f"[{log_context.correlation_id[:8]}] {message}"
            if log_context.server_name:
                formatted_message += f" [server={log_context.server_name}]"
            if log_context.operation:
                formatted_message += f" [op={log_context.operation}]"

        return formatted_message, {"extra": extra_data}

    def debug_protocol(
        self,
        message: str,
        protocol_data: Optional[Dict[str, Any]] = None,
        context: Optional[LogContext] = None,
    ):
        """
        Log MCP protocol message at DEBUG level.

        Used for logging all MCP protocol messages (initialize, list_tools, call_tool, etc.).

        Args:
            message: Log message
            protocol_data: Protocol message data (will be sanitized)
            context: Log context
        """
        ctx = context or LogContext(category=LogCategory.PROTOCOL)
        ctx.category = LogCategory.PROTOCOL

        extra = {"protocol_data": protocol_data} if protocol_data else {}
        formatted_message, extra_dict = self._prepare_message(message, ctx, extra)
        self.logger.debug(formatted_message, extra=extra_dict)

    def info_connection(
        self,
        message: str,
        context: Optional[LogContext] = None,
        **kwargs,
    ):
        """
        Log connection lifecycle event at INFO level.

        Used for connect, disconnect, reconnect events.

        Args:
            message: Log message
            context: Log context
            **kwargs: Additional context fields
        """
        ctx = context or LogContext(category=LogCategory.CONNECTION)
        ctx.category = LogCategory.CONNECTION

        formatted_message, extra_dict = self._prepare_message(message, ctx, kwargs)
        self.logger.info(formatted_message, extra=extra_dict)

    def warn_retry(
        self,
        message: str,
        attempt: int,
        max_attempts: int,
        error: Optional[Exception] = None,
        context: Optional[LogContext] = None,
    ):
        """
        Log retry event at WARNING level.

        Used for retry operations and circuit breaker events.

        Args:
            message: Log message
            attempt: Current retry attempt
            max_attempts: Maximum retry attempts
            error: Error that triggered retry
            context: Log context
        """
        ctx = context or LogContext(category=LogCategory.RETRY)
        ctx.category = LogCategory.RETRY

        extra = {
            "attempt": attempt,
            "max_attempts": max_attempts,
            "error_type": type(error).__name__ if error else None,
            "error_message": str(error) if error else None,
        }

        formatted_message, extra_dict = self._prepare_message(message, ctx, extra)
        self.logger.warning(formatted_message, extra=extra_dict)

    def warn_degradation(
        self,
        message: str,
        metric_name: str,
        current_value: float,
        threshold: float,
        context: Optional[LogContext] = None,
    ):
        """
        Log performance degradation at WARNING level.

        Used when metrics exceed degradation thresholds.

        Args:
            message: Log message
            metric_name: Name of the metric (e.g., 'latency_ms', 'error_rate')
            current_value: Current metric value
            threshold: Threshold that was exceeded
            context: Log context
        """
        ctx = context or LogContext(category=LogCategory.DEGRADATION)
        ctx.category = LogCategory.DEGRADATION

        extra = {
            "metric_name": metric_name,
            "current_value": current_value,
            "threshold": threshold,
            "ratio": current_value / threshold if threshold > 0 else 0,
        }

        formatted_message, extra_dict = self._prepare_message(message, ctx, extra)
        self.logger.warning(formatted_message, extra=extra_dict)

    def error_with_context(
        self,
        message: str,
        error: Exception,
        context: Optional[LogContext] = None,
        **kwargs,
    ):
        """
        Log error with full context at ERROR level.

        Includes exception details, stack trace, and full context.

        Args:
            message: Log message
            error: Exception that occurred
            context: Log context
            **kwargs: Additional context fields
        """
        ctx = context or LogContext()

        extra = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "error_repr": repr(error),
            **kwargs,
        }

        # Include exception info for stack trace
        formatted_message, extra_dict = self._prepare_message(message, ctx, extra)
        self.logger.error(formatted_message, exc_info=error, extra=extra_dict)

    def info_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        success: bool,
        duration_ms: float,
        context: Optional[LogContext] = None,
    ):
        """
        Log tool invocation at INFO level.

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments (will be sanitized)
            success: Whether the call succeeded
            duration_ms: Call duration in milliseconds
            context: Log context
        """
        ctx = context or LogContext(
            category=LogCategory.TOOL_CALL,
            tool_name=tool_name,
            duration_ms=duration_ms,
        )
        ctx.category = LogCategory.TOOL_CALL
        ctx.tool_name = tool_name
        ctx.duration_ms = duration_ms

        extra = {
            "arguments": arguments,
            "success": success,
        }

        status = "succeeded" if success else "failed"
        message = f"Tool call {status}: {tool_name} ({duration_ms:.2f}ms)"

        formatted_message, extra_dict = self._prepare_message(message, ctx, extra)
        self.logger.info(formatted_message, extra=extra_dict)

    def debug_cache(
        self,
        operation: str,
        cache_key: str,
        hit: Optional[bool] = None,
        context: Optional[LogContext] = None,
    ):
        """
        Log cache operation at DEBUG level.

        Args:
            operation: Cache operation (get, set, delete, clear)
            cache_key: Cache key
            hit: Whether cache hit (for get operations)
            context: Log context
        """
        ctx = context or LogContext(category=LogCategory.CACHE)
        ctx.category = LogCategory.CACHE

        extra = {
            "cache_operation": operation,
            "cache_key": cache_key,
        }
        if hit is not None:
            extra["cache_hit"] = hit

        message = f"Cache {operation}: {cache_key}"
        if hit is not None:
            message += f" ({'HIT' if hit else 'MISS'})"

        formatted_message, extra_dict = self._prepare_message(message, ctx, extra)
        self.logger.debug(formatted_message, extra=extra_dict)

    def info_metrics(
        self,
        metrics: Dict[str, float],
        context: Optional[LogContext] = None,
    ):
        """
        Log performance metrics at INFO level.

        Args:
            metrics: Dictionary of metric name -> value
            context: Log context
        """
        ctx = context or LogContext(category=LogCategory.METRICS)
        ctx.category = LogCategory.METRICS

        extra = {"metrics": metrics}

        message = f"Performance metrics: {', '.join(f'{k}={v:.2f}' for k, v in metrics.items())}"

        formatted_message, extra_dict = self._prepare_message(message, ctx, extra)
        self.logger.info(formatted_message, extra=extra_dict)

    def debug(self, message: str, context: Optional[LogContext] = None, **kwargs):
        """Debug level log."""
        formatted_message, extra_dict = self._prepare_message(message, context, kwargs)
        self.logger.debug(formatted_message, extra=extra_dict)

    def info(self, message: str, context: Optional[LogContext] = None, **kwargs):
        """Info level log."""
        formatted_message, extra_dict = self._prepare_message(message, context, kwargs)
        self.logger.info(formatted_message, extra=extra_dict)

    def warning(self, message: str, context: Optional[LogContext] = None, **kwargs):
        """Warning level log."""
        formatted_message, extra_dict = self._prepare_message(message, context, kwargs)
        self.logger.warning(formatted_message, extra=extra_dict)

    def error(self, message: str, context: Optional[LogContext] = None, **kwargs):
        """Error level log."""
        formatted_message, extra_dict = self._prepare_message(message, context, kwargs)
        self.logger.error(formatted_message, extra=extra_dict)


@contextmanager
def log_operation(
    mcp_logger: MCPLogger,
    operation: str,
    context: Optional[LogContext] = None,
    log_success: bool = True,
):
    """
    Context manager for logging operations with timing.

    Automatically logs operation start, duration, and success/failure.

    Args:
        mcp_logger: MCPLogger instance
        operation: Operation name
        context: Log context
        log_success: Whether to log successful completion

    Yields:
        LogContext with correlation_id for the operation

    Example:
        >>> logger = MCPLogger()
        >>> with log_operation(logger, "call_tool", context) as ctx:
        ...     result = await session.call_tool("get_tasks", {})
    """
    ctx = context or LogContext(operation=operation)
    ctx.operation = operation

    start_time = time.perf_counter()

    try:
        mcp_logger.debug(f"Starting operation: {operation}", context=ctx)
        yield ctx

        duration_ms = (time.perf_counter() - start_time) * 1000
        ctx.duration_ms = duration_ms

        if log_success:
            mcp_logger.debug(
                f"Operation completed: {operation} ({duration_ms:.2f}ms)",
                context=ctx
            )
    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        ctx.duration_ms = duration_ms

        mcp_logger.error_with_context(
            f"Operation failed: {operation} ({duration_ms:.2f}ms)",
            error=e,
            context=ctx
        )
        raise


# ============================================================================
# Convenience Functions
# ============================================================================

def get_mcp_logger(
    name: str = "mcp",
    enable_sanitization: bool = True,
    enable_json: bool = False,
) -> MCPLogger:
    """
    Get or create an MCP logger instance.

    Args:
        name: Logger name (usually module name)
        enable_sanitization: Whether to sanitize sensitive data
        enable_json: Whether to format logs as JSON

    Returns:
        MCPLogger instance
    """
    return MCPLogger(
        name=name,
        enable_sanitization=enable_sanitization,
        enable_json=enable_json,
    )


def configure_logging(
    level: str = "INFO",
    format_string: Optional[str] = None,
    enable_json: bool = False,
):
    """
    Configure global logging settings for MCP operations.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        format_string: Custom format string (if not using JSON)
        enable_json: Whether to use JSON formatting
    """
    if format_string is None:
        if enable_json:
            format_string = "%(message)s"  # JSON formatter handles structure
        else:
            format_string = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=format_string,
    )

    # Set MCP-related loggers to the specified level
    for logger_name in [
        "mcp",
        "Tools.adapters.mcp_bridge",
        "Tools.adapters.mcp_config",
        "Tools.adapters.mcp_discovery",
        "Tools.adapters.mcp_pool",
        "Tools.adapters.mcp_health",
        "Tools.adapters.mcp_cache",
        "Tools.adapters.mcp_loadbalancer",
        "Tools.adapters.mcp_retry",
        "Tools.adapters.mcp_validation",
    ]:
        logging.getLogger(logger_name).setLevel(getattr(logging, level.upper()))
