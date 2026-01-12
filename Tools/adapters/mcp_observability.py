"""
MCP Observability: Logging, Metrics, and Monitoring

Comprehensive observability for MCP bridge operations including structured logging,
performance metrics, and health monitoring for production deployments.
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

# Structured logging setup
logger = logging.getLogger(__name__)


@dataclass
class MCPMetrics:
    """
    Performance and operational metrics for MCP operations.
    """

    # Connection metrics
    total_connections: int = 0
    successful_connections: int = 0
    failed_connections: int = 0
    active_connections: int = 0

    # Tool call metrics
    total_tool_calls: int = 0
    successful_tool_calls: int = 0
    failed_tool_calls: int = 0

    # Performance metrics
    call_times: Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list))
    cache_hits: int = 0
    cache_misses: int = 0

    # Health metrics
    circuit_breaker_trips: int = 0
    retry_attempts: int = 0
    server_errors: int = 0

    def record_connection_attempt(self, success: bool) -> None:
        """Record connection attempt."""
        self.total_connections += 1
        if success:
            self.successful_connections += 1
            self.active_connections += 1
        else:
            self.failed_connections += 1

    def record_connection_close(self) -> None:
        """Record connection closure."""
        if self.active_connections > 0:
            self.active_connections -= 1

    def record_tool_call(self, tool_name: str, success: bool, duration: float) -> None:
        """Record tool call metrics."""
        self.total_tool_calls += 1
        if success:
            self.successful_tool_calls += 1
        else:
            self.failed_tool_calls += 1

        self.call_times[tool_name].append(duration)

    def record_cache_access(self, hit: bool) -> None:
        """Record cache hit/miss."""
        if hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1

    def record_error(self, error_type: str) -> None:
        """Record error occurrence."""
        if error_type == "circuit_breaker":
            self.circuit_breaker_trips += 1
        elif error_type == "retry":
            self.retry_attempts += 1
        elif error_type == "server":
            self.server_errors += 1

    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        total_calls = self.total_tool_calls
        success_rate = (
            self.successful_tool_calls / total_calls if total_calls > 0 else 0.0
        )

        cache_total = self.cache_hits + self.cache_misses
        cache_hit_rate = self.cache_hits / cache_total if cache_total > 0 else 0.0

        avg_times = {}
        for tool_name, times in self.call_times.items():
            if times:
                avg_times[tool_name] = sum(times) / len(times)

        return {
            "connections": {
                "total": self.total_connections,
                "successful": self.successful_connections,
                "failed": self.failed_connections,
                "active": self.active_connections,
                "success_rate": (
                    self.successful_connections / self.total_connections
                    if self.total_connections > 0
                    else 0.0
                ),
            },
            "tool_calls": {
                "total": self.total_tool_calls,
                "successful": self.successful_tool_calls,
                "failed": self.failed_tool_calls,
                "success_rate": success_rate,
            },
            "performance": {
                "avg_call_times": avg_times,
                "cache_hit_rate": cache_hit_rate,
            },
            "errors": {
                "circuit_breaker_trips": self.circuit_breaker_trips,
                "retry_attempts": self.retry_attempts,
                "server_errors": self.server_errors,
            },
        }


class MCPLogger:
    """
    Structured logging for MCP operations.
    """

    def __init__(self, server_name: str):
        self.server_name = server_name
        self.logger = logging.getLogger(f"mcp.{server_name}")

    def log_connection_attempt(self, config: Dict[str, Any]) -> None:
        """Log connection attempt."""
        self.logger.info(
            "Attempting MCP server connection",
            extra={
                "server": self.server_name,
                "command": config.get("command"),
                "transport": config.get("transport"),
                "timestamp": datetime.now().isoformat(),
            },
        )

    def log_connection_success(self, duration: float, tools_count: int) -> None:
        """Log successful connection."""
        self.logger.info(
            "MCP server connected successfully",
            extra={
                "server": self.server_name,
                "duration_ms": duration * 1000,
                "tools_discovered": tools_count,
                "timestamp": datetime.now().isoformat(),
            },
        )

    def log_connection_failure(self, error: str, duration: float) -> None:
        """Log connection failure."""
        self.logger.error(
            "MCP server connection failed",
            extra={
                "server": self.server_name,
                "error": error,
                "duration_ms": duration * 1000,
                "timestamp": datetime.now().isoformat(),
            },
        )

    def log_tool_call(
        self, tool_name: str, arguments: Dict[str, Any], duration: float, success: bool
    ) -> None:
        """Log tool call."""
        level = logging.INFO if success else logging.ERROR
        self.logger.log(
            level,
            f"Tool call {'succeeded' if success else 'failed'}",
            extra={
                "server": self.server_name,
                "tool": tool_name,
                "arguments": arguments,
                "duration_ms": duration * 1000,
                "success": success,
                "timestamp": datetime.now().isoformat(),
            },
        )

    def log_cache_access(self, tool_name: str, hit: bool) -> None:
        """Log cache access."""
        self.logger.debug(
            f"Cache {'hit' if hit else 'miss'}",
            extra={
                "server": self.server_name,
                "tool": tool_name,
                "cache_hit": hit,
                "timestamp": datetime.now().isoformat(),
            },
        )

    def log_health_check(self, status: str, details: Optional[Dict] = None) -> None:
        """Log health check."""
        self.logger.info(
            "Health check performed",
            extra={
                "server": self.server_name,
                "status": status,
                "details": details or {},
                "timestamp": datetime.now().isoformat(),
            },
        )

    def log_error(self, error_type: str, error_message: str, context: Optional[Dict] = None) -> None:
        """Log error occurrence."""
        self.logger.error(
            f"MCP error: {error_type}",
            extra={
                "server": self.server_name,
                "error_type": error_type,
                "error_message": error_message,
                "context": context or {},
                "timestamp": datetime.now().isoformat(),
            },
        )


# Global metrics registry
_metrics_registry: Dict[str, MCPMetrics] = {}


def get_metrics(server_name: str) -> MCPMetrics:
    """Get or create metrics for a server."""
    if server_name not in _metrics_registry:
        _metrics_registry[server_name] = MCPMetrics()
    return _metrics_registry[server_name]


def get_all_metrics() -> Dict[str, Dict[str, Any]]:
    """Get metrics for all servers."""
    return {name: metrics.get_summary() for name, metrics in _metrics_registry.items()}


def reset_metrics(server_name: Optional[str] = None) -> None:
    """Reset metrics for a server or all servers."""
    if server_name:
        if server_name in _metrics_registry:
            _metrics_registry[server_name] = MCPMetrics()
    else:
        _metrics_registry.clear()


# Production logging configuration
def configure_production_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> None:
    """
    Configure logging for production use.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional file path for log output
    """
    import logging.config

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
            },
            "standard": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "standard",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "mcp": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False,
            },
        },
        "root": {
            "level": log_level,
            "handlers": ["console"],
        },
    }

    if log_file:
        config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": log_level,
            "formatter": "json",
            "filename": log_file,
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
        }
        config["loggers"]["mcp"]["handlers"].append("file")

    logging.config.dictConfig(config)
