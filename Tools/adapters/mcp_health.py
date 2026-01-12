"""
MCP Server Health Monitoring.

Provides comprehensive health monitoring for MCP servers with periodic checks,
performance metrics collection, and automatic marking of unhealthy servers.

This module monitors server availability, latency, success rates, and other
performance indicators to ensure reliable operation and enable proactive
failure detection.
"""

import asyncio
import logging
import time
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Deque, Optional

from .mcp_config import MCPServerConfig
from .mcp_errors import (
    MCPError,
    MCPServerUnavailableError,
    MCPTimeoutError,
    log_error_with_context,
)
from .mcp_retry import CircuitBreaker, CircuitBreakerRegistry, get_global_registry

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status for MCP servers."""

    HEALTHY = "healthy"
    """Server is operating normally"""

    DEGRADED = "degraded"
    """Server is operational but experiencing issues"""

    UNHEALTHY = "unhealthy"
    """Server is not functioning properly"""

    UNKNOWN = "unknown"
    """Health status cannot be determined"""


@dataclass
class PerformanceMetrics:
    """
    Performance metrics for an MCP server.

    Tracks latency, success rates, and other performance indicators over time.
    """

    total_requests: int = 0
    """Total number of requests made"""

    successful_requests: int = 0
    """Number of successful requests"""

    failed_requests: int = 0
    """Number of failed requests"""

    timeout_requests: int = 0
    """Number of timed out requests"""

    total_latency_ms: float = 0.0
    """Cumulative latency in milliseconds"""

    min_latency_ms: Optional[float] = None
    """Minimum observed latency"""

    max_latency_ms: Optional[float] = None
    """Maximum observed latency"""

    recent_latencies: Deque[float] = field(default_factory=lambda: deque(maxlen=100))
    """Recent latency measurements (last 100)"""

    last_success: Optional[datetime] = None
    """Timestamp of last successful request"""

    last_failure: Optional[datetime] = None
    """Timestamp of last failed request"""

    last_error: Optional[str] = None
    """Description of last error encountered"""

    @property
    def success_rate(self) -> float:
        """
        Calculate success rate as a percentage.

        Returns:
            Success rate (0.0 to 1.0)
        """
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests

    @property
    def failure_rate(self) -> float:
        """
        Calculate failure rate as a percentage.

        Returns:
            Failure rate (0.0 to 1.0)
        """
        return 1.0 - self.success_rate

    @property
    def average_latency_ms(self) -> float:
        """
        Calculate average latency.

        Returns:
            Average latency in milliseconds
        """
        if self.successful_requests == 0:
            return 0.0
        return self.total_latency_ms / self.successful_requests

    @property
    def p95_latency_ms(self) -> Optional[float]:
        """
        Calculate 95th percentile latency from recent samples.

        Returns:
            95th percentile latency in milliseconds, or None if insufficient data
        """
        if len(self.recent_latencies) == 0:
            return None
        sorted_latencies = sorted(self.recent_latencies)
        p95_index = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[p95_index] if p95_index < len(sorted_latencies) else sorted_latencies[-1]

    @property
    def p99_latency_ms(self) -> Optional[float]:
        """
        Calculate 99th percentile latency from recent samples.

        Returns:
            99th percentile latency in milliseconds, or None if insufficient data
        """
        if len(self.recent_latencies) == 0:
            return None
        sorted_latencies = sorted(self.recent_latencies)
        p99_index = int(len(sorted_latencies) * 0.99)
        return sorted_latencies[p99_index] if p99_index < len(sorted_latencies) else sorted_latencies[-1]

    def record_success(self, latency_ms: float) -> None:
        """
        Record a successful request.

        Args:
            latency_ms: Request latency in milliseconds
        """
        self.total_requests += 1
        self.successful_requests += 1
        self.total_latency_ms += latency_ms
        self.recent_latencies.append(latency_ms)
        self.last_success = datetime.now()

        # Update min/max latency
        if self.min_latency_ms is None or latency_ms < self.min_latency_ms:
            self.min_latency_ms = latency_ms
        if self.max_latency_ms is None or latency_ms > self.max_latency_ms:
            self.max_latency_ms = latency_ms

    def record_failure(self, error: Optional[Exception] = None, is_timeout: bool = False) -> None:
        """
        Record a failed request.

        Args:
            error: Exception that caused the failure
            is_timeout: Whether the failure was due to timeout
        """
        self.total_requests += 1
        self.failed_requests += 1
        self.last_failure = datetime.now()

        if is_timeout:
            self.timeout_requests += 1

        if error:
            self.last_error = str(error)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert metrics to dictionary for serialization.

        Returns:
            Dictionary representation of metrics
        """
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "timeout_requests": self.timeout_requests,
            "success_rate": self.success_rate,
            "failure_rate": self.failure_rate,
            "average_latency_ms": self.average_latency_ms,
            "min_latency_ms": self.min_latency_ms,
            "max_latency_ms": self.max_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "p99_latency_ms": self.p99_latency_ms,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "last_failure": self.last_failure.isoformat() if self.last_failure else None,
            "last_error": self.last_error,
        }


@dataclass
class HealthCheckConfig:
    """Configuration for health check behavior."""

    check_interval: float = 30.0
    """Interval between health checks (seconds)"""

    check_timeout: float = 10.0
    """Timeout for individual health check (seconds)"""

    healthy_threshold: int = 2
    """Consecutive successful checks to mark as healthy"""

    unhealthy_threshold: int = 3
    """Consecutive failed checks to mark as unhealthy"""

    degraded_latency_ms: float = 1000.0
    """Latency threshold for degraded status (milliseconds)"""

    degraded_success_rate: float = 0.9
    """Success rate threshold for degraded status (0.0-1.0)"""

    enable_auto_checks: bool = True
    """Whether to run automatic periodic health checks"""

    custom_check_function: Optional[Callable] = None
    """Optional custom health check function"""


@dataclass
class HealthCheckResult:
    """
    Result of a health check operation.

    Contains health status, metrics, and diagnostic information.
    """

    server_name: str
    """Name of the server that was checked"""

    status: HealthStatus
    """Current health status"""

    timestamp: datetime = field(default_factory=datetime.now)
    """When the health check was performed"""

    latency_ms: Optional[float] = None
    """Latency of the health check (if successful)"""

    error: Optional[str] = None
    """Error message (if failed)"""

    metrics: Optional[PerformanceMetrics] = None
    """Performance metrics for the server"""

    circuit_breaker_open: bool = False
    """Whether circuit breaker is open for this server"""

    details: dict[str, Any] = field(default_factory=dict)
    """Additional diagnostic details"""

    @property
    def is_healthy(self) -> bool:
        """Check if server is healthy."""
        return self.status == HealthStatus.HEALTHY

    @property
    def is_degraded(self) -> bool:
        """Check if server is degraded."""
        return self.status == HealthStatus.DEGRADED

    @property
    def is_unhealthy(self) -> bool:
        """Check if server is unhealthy."""
        return self.status == HealthStatus.UNHEALTHY

    def to_dict(self) -> dict[str, Any]:
        """
        Convert result to dictionary for serialization.

        Returns:
            Dictionary representation of health check result
        """
        return {
            "server_name": self.server_name,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "latency_ms": self.latency_ms,
            "error": self.error,
            "circuit_breaker_open": self.circuit_breaker_open,
            "metrics": self.metrics.to_dict() if self.metrics else None,
            "details": self.details,
        }


class HealthMonitor:
    """
    Monitors health and performance of MCP servers.

    Performs periodic health checks, collects metrics, and automatically
    marks unhealthy servers. Integrates with circuit breakers for fault
    tolerance.
    """

    def __init__(
        self,
        server_config: MCPServerConfig,
        config: Optional[HealthCheckConfig] = None,
        health_check_function: Optional[Callable] = None,
    ):
        """
        Initialize health monitor for an MCP server.

        Args:
            server_config: Configuration for the MCP server to monitor
            config: Health check configuration
            health_check_function: Async function to perform health checks
                                   Should accept no args and return True if healthy
        """
        self.server_config = server_config
        self.config = config or HealthCheckConfig()
        self.health_check_function = health_check_function or self._default_health_check

        self.metrics = PerformanceMetrics()
        self._current_status = HealthStatus.UNKNOWN
        self._consecutive_successes = 0
        self._consecutive_failures = 0
        self._health_check_task: Optional[asyncio.Task] = None
        self._circuit_breaker_registry = get_global_registry()
        self._running = False
        self._lock = asyncio.Lock()

        logger.info(f"Health monitor initialized for server: {self.server_config.name}")

    @property
    def server_name(self) -> str:
        """Get the server name."""
        return self.server_config.name

    @property
    def status(self) -> HealthStatus:
        """Get current health status."""
        return self._current_status

    @property
    def is_healthy(self) -> bool:
        """Check if server is currently healthy."""
        return self._current_status == HealthStatus.HEALTHY

    @property
    def is_running(self) -> bool:
        """Check if health monitor is running."""
        return self._running

    async def _default_health_check(self) -> bool:
        """
        Default health check implementation.

        Checks if circuit breaker is closed and recent success rate is acceptable.

        Returns:
            True if server appears healthy, False otherwise
        """
        # Check circuit breaker
        circuit_breaker = await self._circuit_breaker_registry.get_breaker(self.server_name)
        if circuit_breaker and circuit_breaker.is_open():
            logger.debug(f"Health check failed: circuit breaker is open for {self.server_name}")
            return False

        # Check recent performance
        if self.metrics.total_requests > 0:
            # If we have recent data, check success rate
            if self.metrics.success_rate < self.config.degraded_success_rate:
                logger.debug(
                    f"Health check failed: success rate {self.metrics.success_rate:.2%} "
                    f"below threshold {self.config.degraded_success_rate:.2%}"
                )
                return False

        return True

    async def perform_health_check(self) -> HealthCheckResult:
        """
        Perform a single health check.

        Returns:
            HealthCheckResult with current health status and metrics

        This method is safe to call concurrently and will not interfere
        with the automatic health check loop.
        """
        async with self._lock:
            start_time = time.time()
            error_msg = None
            latency_ms = None
            check_succeeded = False

            try:
                # Execute health check with timeout
                check_succeeded = await asyncio.wait_for(
                    self.health_check_function(),
                    timeout=self.config.check_timeout,
                )

                latency_ms = (time.time() - start_time) * 1000

                if check_succeeded:
                    self._consecutive_successes += 1
                    self._consecutive_failures = 0
                    logger.debug(
                        f"Health check passed for {self.server_name} "
                        f"(latency: {latency_ms:.2f}ms, consecutive: {self._consecutive_successes})"
                    )
                else:
                    self._consecutive_failures += 1
                    self._consecutive_successes = 0
                    error_msg = "Health check returned False"
                    logger.warning(
                        f"Health check failed for {self.server_name} "
                        f"(consecutive: {self._consecutive_failures})"
                    )

            except asyncio.TimeoutError:
                latency_ms = (time.time() - start_time) * 1000
                self._consecutive_failures += 1
                self._consecutive_successes = 0
                error_msg = f"Health check timed out after {self.config.check_timeout}s"
                logger.warning(f"{error_msg} for {self.server_name}")

            except Exception as e:
                latency_ms = (time.time() - start_time) * 1000
                self._consecutive_failures += 1
                self._consecutive_successes = 0
                error_msg = f"Health check error: {str(e)}"
                log_error_with_context(
                    e,
                    component="health_monitor",
                    additional_context={"server": self.server_name},
                )

            # Determine health status
            new_status = self._determine_health_status(
                check_succeeded=check_succeeded,
                latency_ms=latency_ms,
                error_msg=error_msg,
            )

            # Update status if changed
            if new_status != self._current_status:
                old_status = self._current_status
                self._current_status = new_status
                logger.info(
                    f"Health status changed for {self.server_name}: {old_status.value} → {new_status.value}"
                )

            # Get circuit breaker status
            circuit_breaker = await self._circuit_breaker_registry.get_breaker(self.server_name)
            circuit_breaker_open = circuit_breaker.is_open() if circuit_breaker else False

            # Create result
            return HealthCheckResult(
                server_name=self.server_name,
                status=self._current_status,
                latency_ms=latency_ms,
                error=error_msg,
                metrics=self.metrics,
                circuit_breaker_open=circuit_breaker_open,
                details={
                    "consecutive_successes": self._consecutive_successes,
                    "consecutive_failures": self._consecutive_failures,
                    "circuit_breaker_state": circuit_breaker.state.value if circuit_breaker else "unknown",
                },
            )

    def _determine_health_status(
        self,
        check_succeeded: bool,
        latency_ms: Optional[float],
        error_msg: Optional[str],
    ) -> HealthStatus:
        """
        Determine health status based on check results and thresholds.

        Args:
            check_succeeded: Whether the health check succeeded
            latency_ms: Latency of the check
            error_msg: Error message if check failed

        Returns:
            Determined health status
        """
        # Unhealthy if consecutive failures exceed threshold
        if self._consecutive_failures >= self.config.unhealthy_threshold:
            return HealthStatus.UNHEALTHY

        # Healthy if consecutive successes exceed threshold
        if self._consecutive_successes >= self.config.healthy_threshold:
            # Check for degraded performance indicators
            if latency_ms and latency_ms > self.config.degraded_latency_ms:
                logger.debug(
                    f"Server {self.server_name} is degraded: high latency ({latency_ms:.2f}ms)"
                )
                return HealthStatus.DEGRADED

            # Only check success rate if we have meaningful request data
            if self.metrics.total_requests >= 10 and self.metrics.success_rate < self.config.degraded_success_rate:
                logger.debug(
                    f"Server {self.server_name} is degraded: low success rate ({self.metrics.success_rate:.2%})"
                )
                return HealthStatus.DEGRADED

            return HealthStatus.HEALTHY

        # Unknown if we don't have enough data
        return HealthStatus.UNKNOWN

    async def _health_check_loop(self) -> None:
        """
        Background task that performs periodic health checks.

        Runs until stop() is called.
        """
        logger.info(
            f"Starting health check loop for {self.server_name} "
            f"(interval: {self.config.check_interval}s)"
        )

        while self._running:
            try:
                # Perform health check
                result = await self.perform_health_check()

                # Log result
                logger.debug(
                    f"Health check completed for {self.server_name}: "
                    f"status={result.status.value}, latency={result.latency_ms:.2f}ms"
                    if result.latency_ms
                    else f"status={result.status.value}"
                )

                # Wait for next check
                await asyncio.sleep(self.config.check_interval)

            except asyncio.CancelledError:
                logger.info(f"Health check loop cancelled for {self.server_name}")
                break
            except Exception as e:
                log_error_with_context(
                    e,
                    component="health_check_loop",
                    additional_context={"server": self.server_name},
                )
                # Continue running even if check fails
                await asyncio.sleep(self.config.check_interval)

        logger.info(f"Health check loop stopped for {self.server_name}")

    async def start(self) -> None:
        """
        Start automatic health monitoring.

        Begins periodic health checks in the background.
        """
        if self._running:
            logger.warning(f"Health monitor already running for {self.server_name}")
            return

        if not self.config.enable_auto_checks:
            logger.info(f"Auto health checks disabled for {self.server_name}")
            return

        self._running = True
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info(f"Health monitor started for {self.server_name}")

    async def stop(self) -> None:
        """
        Stop automatic health monitoring.

        Cancels the background health check task.
        """
        if not self._running:
            return

        self._running = False

        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None

        logger.info(f"Health monitor stopped for {self.server_name}")

    def record_request(self, success: bool, latency_ms: float, error: Optional[Exception] = None) -> None:
        """
        Record metrics for a request.

        Args:
            success: Whether the request succeeded
            latency_ms: Request latency in milliseconds
            error: Exception if request failed
        """
        if success:
            self.metrics.record_success(latency_ms)
        else:
            is_timeout = isinstance(error, (asyncio.TimeoutError, MCPTimeoutError))
            self.metrics.record_failure(error=error, is_timeout=is_timeout)

    async def get_health_status(self) -> HealthCheckResult:
        """
        Get current health status synchronously.

        Returns:
            Current health check result with metrics

        Note: This returns cached status without performing a new check.
        Use perform_health_check() for a fresh check.
        """
        circuit_breaker = await self._circuit_breaker_registry.get_breaker(self.server_name)
        circuit_breaker_open = circuit_breaker.is_open() if circuit_breaker else False

        return HealthCheckResult(
            server_name=self.server_name,
            status=self._current_status,
            metrics=self.metrics,
            circuit_breaker_open=circuit_breaker_open,
            details={
                "consecutive_successes": self._consecutive_successes,
                "consecutive_failures": self._consecutive_failures,
                "circuit_breaker_state": circuit_breaker.state.value if circuit_breaker else "unknown",
            },
        )

    def reset_metrics(self) -> None:
        """Reset performance metrics."""
        self.metrics = PerformanceMetrics()
        logger.info(f"Metrics reset for {self.server_name}")

    async def __aenter__(self):
        """Context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.stop()
        return False


class HealthMonitorRegistry:
    """
    Registry for managing health monitors across multiple servers.

    Provides centralized access to health monitors and aggregate health status.
    """

    def __init__(self):
        """Initialize the registry."""
        self._monitors: dict[str, HealthMonitor] = {}
        self._lock = asyncio.Lock()
        logger.debug("Health monitor registry initialized")

    async def register_monitor(
        self,
        server_config: MCPServerConfig,
        config: Optional[HealthCheckConfig] = None,
        health_check_function: Optional[Callable] = None,
        start_immediately: bool = True,
    ) -> HealthMonitor:
        """
        Register a health monitor for a server.

        Args:
            server_config: Server configuration
            config: Health check configuration
            health_check_function: Custom health check function
            start_immediately: Whether to start monitoring immediately

        Returns:
            Registered health monitor
        """
        async with self._lock:
            if server_config.name in self._monitors:
                logger.warning(f"Health monitor already registered for {server_config.name}")
                return self._monitors[server_config.name]

            monitor = HealthMonitor(
                server_config=server_config,
                config=config,
                health_check_function=health_check_function,
            )

            if start_immediately and (config is None or config.enable_auto_checks):
                await monitor.start()

            self._monitors[server_config.name] = monitor
            logger.info(f"Health monitor registered for {server_config.name}")

            return monitor

    async def unregister_monitor(self, server_name: str) -> None:
        """
        Unregister and stop a health monitor.

        Args:
            server_name: Name of the server
        """
        async with self._lock:
            monitor = self._monitors.pop(server_name, None)
            if monitor:
                await monitor.stop()
                logger.info(f"Health monitor unregistered for {server_name}")

    def get_monitor(self, server_name: str) -> Optional[HealthMonitor]:
        """
        Get health monitor for a server.

        Args:
            server_name: Name of the server

        Returns:
            Health monitor if registered, None otherwise
        """
        return self._monitors.get(server_name)

    def get_all_monitors(self) -> dict[str, HealthMonitor]:
        """
        Get all registered health monitors.

        Returns:
            Dictionary mapping server names to health monitors
        """
        return self._monitors.copy()

    async def get_all_health_status(self) -> dict[str, HealthCheckResult]:
        """
        Get health status for all registered servers.

        Returns:
            Dictionary mapping server names to health check results
        """
        results = {}
        for name, monitor in self._monitors.items():
            results[name] = await monitor.get_health_status()
        return results

    async def perform_all_health_checks(self) -> dict[str, HealthCheckResult]:
        """
        Perform fresh health checks on all servers concurrently.

        Returns:
            Dictionary mapping server names to health check results
        """
        if not self._monitors:
            return {}

        # Perform all checks concurrently
        check_tasks = {
            name: monitor.perform_health_check()
            for name, monitor in self._monitors.items()
        }

        results = {}
        for name, task in check_tasks.items():
            try:
                results[name] = await task
            except Exception as e:
                logger.error(f"Health check failed for {name}: {e}")
                # Create failed result
                results[name] = HealthCheckResult(
                    server_name=name,
                    status=HealthStatus.UNHEALTHY,
                    error=str(e),
                )

        return results

    def get_healthy_servers(self) -> list[str]:
        """
        Get list of healthy server names.

        Returns:
            List of server names with healthy status
        """
        return [
            name
            for name, monitor in self._monitors.items()
            if monitor.is_healthy
        ]

    def get_unhealthy_servers(self) -> list[str]:
        """
        Get list of unhealthy server names.

        Returns:
            List of server names with unhealthy status
        """
        return [
            name
            for name, monitor in self._monitors.items()
            if monitor.status == HealthStatus.UNHEALTHY
        ]

    async def start_all(self) -> None:
        """Start health monitoring for all registered servers."""
        for monitor in self._monitors.values():
            if not monitor.is_running:
                await monitor.start()
        logger.info(f"Started health monitoring for {len(self._monitors)} servers")

    async def stop_all(self) -> None:
        """Stop health monitoring for all registered servers."""
        for monitor in self._monitors.values():
            await monitor.stop()
        logger.info(f"Stopped health monitoring for {len(self._monitors)} servers")

    async def close(self) -> None:
        """
        Close the registry and stop all monitors.

        Alias for stop_all() for consistency with other components.
        """
        await self.stop_all()
        self._monitors.clear()
        logger.info("Health monitor registry closed")

    async def __aenter__(self):
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()
        return False


# Global registry singleton
_global_health_monitor_registry: Optional[HealthMonitorRegistry] = None


def get_global_health_monitor_registry() -> HealthMonitorRegistry:
    """
    Get the global health monitor registry singleton.

    Returns:
        Global health monitor registry instance
    """
    global _global_health_monitor_registry
    if _global_health_monitor_registry is None:
        _global_health_monitor_registry = HealthMonitorRegistry()
    return _global_health_monitor_registry


# Convenience functions


async def create_health_monitor(
    server_config: MCPServerConfig,
    config: Optional[HealthCheckConfig] = None,
    health_check_function: Optional[Callable] = None,
    start: bool = True,
) -> HealthMonitor:
    """
    Create and optionally start a health monitor.

    Args:
        server_config: Server configuration
        config: Health check configuration
        health_check_function: Custom health check function
        start: Whether to start monitoring immediately

    Returns:
        Created health monitor
    """
    monitor = HealthMonitor(
        server_config=server_config,
        config=config,
        health_check_function=health_check_function,
    )

    if start:
        await monitor.start()

    return monitor


async def check_server_health(
    server_name: str,
    registry: Optional[HealthMonitorRegistry] = None,
) -> Optional[HealthCheckResult]:
    """
    Check health of a specific server.

    Args:
        server_name: Name of the server to check
        registry: Health monitor registry (uses global if not provided)

    Returns:
        Health check result, or None if server not found
    """
    if registry is None:
        registry = get_global_health_monitor_registry()

    monitor = registry.get_monitor(server_name)
    if monitor is None:
        logger.warning(f"No health monitor found for server: {server_name}")
        return None

    return await monitor.perform_health_check()
