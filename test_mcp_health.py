"""
Tests for MCP Server Health Monitoring.

Verifies health check functionality, performance metrics, and monitoring.
"""

import asyncio
import pytest
from datetime import datetime, timedelta

from Tools.adapters.mcp_config import MCPServerConfig, StdioConfig
from Tools.adapters.mcp_health import (
    HealthCheckConfig,
    HealthCheckResult,
    HealthMonitor,
    HealthMonitorRegistry,
    HealthStatus,
    PerformanceMetrics,
    check_server_health,
    create_health_monitor,
    get_global_health_monitor_registry,
)


class TestHealthStatus:
    """Test HealthStatus enum."""

    def test_health_statuses(self):
        """Test that health statuses are defined correctly."""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.UNKNOWN.value == "unknown"


class TestPerformanceMetrics:
    """Test PerformanceMetrics dataclass."""

    def test_initial_state(self):
        """Test initial metrics state."""
        metrics = PerformanceMetrics()

        assert metrics.total_requests == 0
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 0
        assert metrics.timeout_requests == 0
        assert metrics.success_rate == 0.0
        assert metrics.failure_rate == 1.0
        assert metrics.average_latency_ms == 0.0
        assert metrics.min_latency_ms is None
        assert metrics.max_latency_ms is None

    def test_record_success(self):
        """Test recording successful requests."""
        metrics = PerformanceMetrics()

        metrics.record_success(100.0)
        metrics.record_success(200.0)
        metrics.record_success(150.0)

        assert metrics.total_requests == 3
        assert metrics.successful_requests == 3
        assert metrics.failed_requests == 0
        assert metrics.success_rate == 1.0
        assert metrics.failure_rate == 0.0
        assert metrics.average_latency_ms == 150.0
        assert metrics.min_latency_ms == 100.0
        assert metrics.max_latency_ms == 200.0
        assert len(metrics.recent_latencies) == 3
        assert metrics.last_success is not None

    def test_record_failure(self):
        """Test recording failed requests."""
        metrics = PerformanceMetrics()

        metrics.record_failure(error=Exception("Test error"))
        metrics.record_failure(error=Exception("Timeout"), is_timeout=True)

        assert metrics.total_requests == 2
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 2
        assert metrics.timeout_requests == 1
        assert metrics.success_rate == 0.0
        assert metrics.failure_rate == 1.0
        assert metrics.last_failure is not None
        assert metrics.last_error == "Timeout"

    def test_mixed_requests(self):
        """Test recording mixed successful and failed requests."""
        metrics = PerformanceMetrics()

        metrics.record_success(100.0)
        metrics.record_success(200.0)
        metrics.record_failure()
        metrics.record_success(150.0)

        assert metrics.total_requests == 4
        assert metrics.successful_requests == 3
        assert metrics.failed_requests == 1
        assert metrics.success_rate == 0.75
        assert metrics.failure_rate == 0.25

    def test_percentile_latencies(self):
        """Test percentile latency calculations."""
        metrics = PerformanceMetrics()

        # Record 100 latencies from 1 to 100ms
        for i in range(1, 101):
            metrics.record_success(float(i))

        p95 = metrics.p95_latency_ms
        p99 = metrics.p99_latency_ms

        assert p95 is not None
        assert p99 is not None
        assert 94.0 <= p95 <= 96.0  # Should be around 95
        assert 98.0 <= p99 <= 100.0  # Should be around 99

    def test_to_dict(self):
        """Test converting metrics to dictionary."""
        metrics = PerformanceMetrics()
        metrics.record_success(100.0)
        metrics.record_failure()

        data = metrics.to_dict()

        assert data["total_requests"] == 2
        assert data["successful_requests"] == 1
        assert data["failed_requests"] == 1
        assert data["success_rate"] == 0.5
        assert data["average_latency_ms"] == 100.0
        assert "last_success" in data
        assert "last_failure" in data


class TestHealthCheckConfig:
    """Test HealthCheckConfig dataclass."""

    def test_default_config(self):
        """Test default health check configuration."""
        config = HealthCheckConfig()

        assert config.check_interval == 30.0
        assert config.check_timeout == 10.0
        assert config.healthy_threshold == 2
        assert config.unhealthy_threshold == 3
        assert config.degraded_latency_ms == 1000.0
        assert config.degraded_success_rate == 0.9
        assert config.enable_auto_checks is True
        assert config.custom_check_function is None

    def test_custom_config(self):
        """Test custom health check configuration."""
        config = HealthCheckConfig(
            check_interval=60.0,
            check_timeout=5.0,
            healthy_threshold=3,
            unhealthy_threshold=5,
            enable_auto_checks=False,
        )

        assert config.check_interval == 60.0
        assert config.check_timeout == 5.0
        assert config.healthy_threshold == 3
        assert config.unhealthy_threshold == 5
        assert config.enable_auto_checks is False


class TestHealthCheckResult:
    """Test HealthCheckResult dataclass."""

    def test_healthy_result(self):
        """Test creating a healthy result."""
        result = HealthCheckResult(
            server_name="test-server",
            status=HealthStatus.HEALTHY,
            latency_ms=50.0,
        )

        assert result.server_name == "test-server"
        assert result.status == HealthStatus.HEALTHY
        assert result.latency_ms == 50.0
        assert result.error is None
        assert result.is_healthy is True
        assert result.is_degraded is False
        assert result.is_unhealthy is False

    def test_unhealthy_result(self):
        """Test creating an unhealthy result."""
        result = HealthCheckResult(
            server_name="test-server",
            status=HealthStatus.UNHEALTHY,
            error="Connection failed",
        )

        assert result.status == HealthStatus.UNHEALTHY
        assert result.error == "Connection failed"
        assert result.is_healthy is False
        assert result.is_unhealthy is True

    def test_to_dict(self):
        """Test converting result to dictionary."""
        metrics = PerformanceMetrics()
        metrics.record_success(100.0)

        result = HealthCheckResult(
            server_name="test-server",
            status=HealthStatus.HEALTHY,
            latency_ms=50.0,
            metrics=metrics,
            circuit_breaker_open=False,
        )

        data = result.to_dict()

        assert data["server_name"] == "test-server"
        assert data["status"] == "healthy"
        assert data["latency_ms"] == 50.0
        assert data["circuit_breaker_open"] is False
        assert data["metrics"] is not None
        assert isinstance(data["metrics"], dict)


@pytest.mark.asyncio
class TestHealthMonitor:
    """Test HealthMonitor class."""

    def create_test_server_config(self, name: str = "test-server") -> MCPServerConfig:
        """Create a test server configuration."""
        return MCPServerConfig(
            name=name,
            transport=StdioConfig(
                command="node",
                args=["test.js"],
            ),
        )

    async def test_monitor_initialization(self):
        """Test health monitor initialization."""
        config = self.create_test_server_config()
        monitor = HealthMonitor(config)

        assert monitor.server_name == "test-server"
        assert monitor.status == HealthStatus.UNKNOWN
        assert monitor.is_healthy is False
        assert monitor.is_running is False
        assert isinstance(monitor.metrics, PerformanceMetrics)

    async def test_custom_health_check_function(self):
        """Test custom health check function."""
        config = self.create_test_server_config()

        call_count = 0

        async def custom_check():
            nonlocal call_count
            call_count += 1
            return True

        monitor = HealthMonitor(
            config,
            health_check_function=custom_check,
        )

        result = await monitor.perform_health_check()

        assert call_count == 1
        assert result.status == HealthStatus.UNKNOWN  # Need multiple successes for HEALTHY

    async def test_perform_health_check_success(self):
        """Test performing a successful health check."""
        config = self.create_test_server_config()

        async def always_healthy():
            return True

        monitor = HealthMonitor(
            config,
            health_check_function=always_healthy,
        )

        # Perform multiple checks to reach healthy threshold
        for _ in range(3):
            result = await monitor.perform_health_check()

        assert result.is_healthy
        assert result.latency_ms is not None
        assert result.error is None
        assert monitor.status == HealthStatus.HEALTHY

    async def test_perform_health_check_failure(self):
        """Test performing a failed health check."""
        config = self.create_test_server_config()

        async def always_unhealthy():
            return False

        monitor = HealthMonitor(
            config,
            health_check_function=always_unhealthy,
        )

        # Perform multiple checks to reach unhealthy threshold
        for _ in range(4):
            result = await monitor.perform_health_check()

        assert result.is_unhealthy
        assert result.error is not None
        assert monitor.status == HealthStatus.UNHEALTHY

    async def test_perform_health_check_timeout(self):
        """Test health check timeout."""
        config = self.create_test_server_config()

        async def slow_check():
            await asyncio.sleep(2.0)
            return True

        health_config = HealthCheckConfig(check_timeout=0.1)
        monitor = HealthMonitor(
            config,
            config=health_config,
            health_check_function=slow_check,
        )

        result = await monitor.perform_health_check()

        assert result.error is not None
        assert "timed out" in result.error.lower()

    async def test_record_request_metrics(self):
        """Test recording request metrics."""
        config = self.create_test_server_config()
        monitor = HealthMonitor(config)

        # Record successful requests
        monitor.record_request(success=True, latency_ms=100.0)
        monitor.record_request(success=True, latency_ms=200.0)

        # Record failed request
        monitor.record_request(
            success=False,
            latency_ms=50.0,
            error=Exception("Test error"),
        )

        metrics = monitor.metrics
        assert metrics.total_requests == 3
        assert metrics.successful_requests == 2
        assert metrics.failed_requests == 1
        assert metrics.success_rate == pytest.approx(0.666, rel=0.01)

    async def test_get_health_status(self):
        """Test getting current health status."""
        config = self.create_test_server_config()
        monitor = HealthMonitor(config)

        status = await monitor.get_health_status()

        assert isinstance(status, HealthCheckResult)
        assert status.server_name == "test-server"
        assert status.status == HealthStatus.UNKNOWN
        assert status.metrics is not None

    async def test_reset_metrics(self):
        """Test resetting metrics."""
        config = self.create_test_server_config()
        monitor = HealthMonitor(config)

        # Record some metrics
        monitor.record_request(success=True, latency_ms=100.0)
        monitor.record_request(success=False, latency_ms=50.0)

        assert monitor.metrics.total_requests == 2

        # Reset metrics
        monitor.reset_metrics()

        assert monitor.metrics.total_requests == 0
        assert monitor.metrics.successful_requests == 0
        assert monitor.metrics.failed_requests == 0

    async def test_start_stop_monitoring(self):
        """Test starting and stopping health monitoring."""
        config = self.create_test_server_config()

        async def quick_check():
            return True

        health_config = HealthCheckConfig(
            check_interval=0.1,  # Fast checks for testing
            enable_auto_checks=True,
        )

        monitor = HealthMonitor(
            config,
            config=health_config,
            health_check_function=quick_check,
        )

        # Start monitoring
        await monitor.start()
        assert monitor.is_running is True

        # Let it run for a bit
        await asyncio.sleep(0.3)

        # Stop monitoring
        await monitor.stop()
        assert monitor.is_running is False

    async def test_context_manager(self):
        """Test using health monitor as context manager."""
        config = self.create_test_server_config()

        async def quick_check():
            return True

        health_config = HealthCheckConfig(
            check_interval=0.1,
            enable_auto_checks=True,
        )

        async with HealthMonitor(
            config,
            config=health_config,
            health_check_function=quick_check,
        ) as monitor:
            assert monitor.is_running is True
            await asyncio.sleep(0.2)

        # Should be stopped after context exit
        assert monitor.is_running is False


@pytest.mark.asyncio
class TestHealthMonitorRegistry:
    """Test HealthMonitorRegistry class."""

    def create_test_server_config(self, name: str) -> MCPServerConfig:
        """Create a test server configuration."""
        return MCPServerConfig(
            name=name,
            transport=StdioConfig(
                command="node",
                args=["test.js"],
            ),
        )

    async def test_registry_initialization(self):
        """Test registry initialization."""
        registry = HealthMonitorRegistry()

        monitors = registry.get_all_monitors()
        assert len(monitors) == 0

    async def test_register_monitor(self):
        """Test registering a health monitor."""
        registry = HealthMonitorRegistry()
        config = self.create_test_server_config("server1")

        monitor = await registry.register_monitor(
            config,
            start_immediately=False,
        )

        assert monitor is not None
        assert monitor.server_name == "server1"
        assert registry.get_monitor("server1") is monitor

    async def test_register_duplicate(self):
        """Test registering duplicate monitor."""
        registry = HealthMonitorRegistry()
        config = self.create_test_server_config("server1")

        monitor1 = await registry.register_monitor(config, start_immediately=False)
        monitor2 = await registry.register_monitor(config, start_immediately=False)

        # Should return same monitor
        assert monitor1 is monitor2

    async def test_unregister_monitor(self):
        """Test unregistering a health monitor."""
        registry = HealthMonitorRegistry()
        config = self.create_test_server_config("server1")

        await registry.register_monitor(config, start_immediately=False)
        assert registry.get_monitor("server1") is not None

        await registry.unregister_monitor("server1")
        assert registry.get_monitor("server1") is None

    async def test_get_all_monitors(self):
        """Test getting all monitors."""
        registry = HealthMonitorRegistry()

        config1 = self.create_test_server_config("server1")
        config2 = self.create_test_server_config("server2")

        await registry.register_monitor(config1, start_immediately=False)
        await registry.register_monitor(config2, start_immediately=False)

        monitors = registry.get_all_monitors()
        assert len(monitors) == 2
        assert "server1" in monitors
        assert "server2" in monitors

    async def test_get_all_health_status(self):
        """Test getting health status for all servers."""
        registry = HealthMonitorRegistry()

        config1 = self.create_test_server_config("server1")
        config2 = self.create_test_server_config("server2")

        await registry.register_monitor(config1, start_immediately=False)
        await registry.register_monitor(config2, start_immediately=False)

        results = await registry.get_all_health_status()

        assert len(results) == 2
        assert "server1" in results
        assert "server2" in results
        assert isinstance(results["server1"], HealthCheckResult)
        assert isinstance(results["server2"], HealthCheckResult)

    async def test_perform_all_health_checks(self):
        """Test performing health checks on all servers."""
        registry = HealthMonitorRegistry()

        async def healthy_check():
            return True

        config1 = self.create_test_server_config("server1")
        monitor1 = await registry.register_monitor(config1, start_immediately=False)
        monitor1.health_check_function = healthy_check

        config2 = self.create_test_server_config("server2")
        monitor2 = await registry.register_monitor(config2, start_immediately=False)
        monitor2.health_check_function = healthy_check

        results = await registry.perform_all_health_checks()

        assert len(results) == 2
        assert "server1" in results
        assert "server2" in results

    async def test_get_healthy_servers(self):
        """Test getting list of healthy servers."""
        registry = HealthMonitorRegistry()

        async def healthy_check():
            return True

        config = self.create_test_server_config("server1")
        monitor = await registry.register_monitor(config, start_immediately=False)
        monitor.health_check_function = healthy_check

        # Perform checks to reach healthy status
        for _ in range(3):
            await monitor.perform_health_check()

        healthy_servers = registry.get_healthy_servers()
        assert "server1" in healthy_servers

    async def test_get_unhealthy_servers(self):
        """Test getting list of unhealthy servers."""
        registry = HealthMonitorRegistry()

        async def unhealthy_check():
            return False

        config = self.create_test_server_config("server1")
        monitor = await registry.register_monitor(config, start_immediately=False)
        monitor.health_check_function = unhealthy_check

        # Perform checks to reach unhealthy status
        for _ in range(4):
            await monitor.perform_health_check()

        unhealthy_servers = registry.get_unhealthy_servers()
        assert "server1" in unhealthy_servers

    async def test_start_stop_all(self):
        """Test starting and stopping all monitors."""
        registry = HealthMonitorRegistry()

        async def quick_check():
            return True

        health_config = HealthCheckConfig(
            check_interval=0.1,
            enable_auto_checks=True,
        )

        config1 = self.create_test_server_config("server1")
        config2 = self.create_test_server_config("server2")

        await registry.register_monitor(
            config1,
            config=health_config,
            health_check_function=quick_check,
            start_immediately=False,
        )
        await registry.register_monitor(
            config2,
            config=health_config,
            health_check_function=quick_check,
            start_immediately=False,
        )

        # Start all
        await registry.start_all()

        monitor1 = registry.get_monitor("server1")
        monitor2 = registry.get_monitor("server2")
        assert monitor1.is_running is True
        assert monitor2.is_running is True

        # Stop all
        await registry.stop_all()
        assert monitor1.is_running is False
        assert monitor2.is_running is False

    async def test_context_manager(self):
        """Test using registry as context manager."""
        async with HealthMonitorRegistry() as registry:
            config = self.create_test_server_config("server1")
            await registry.register_monitor(config, start_immediately=False)

            assert len(registry.get_all_monitors()) == 1

        # Should be closed after context exit
        assert len(registry.get_all_monitors()) == 0


@pytest.mark.asyncio
class TestConvenienceFunctions:
    """Test convenience functions."""

    def create_test_server_config(self, name: str = "test-server") -> MCPServerConfig:
        """Create a test server configuration."""
        return MCPServerConfig(
            name=name,
            transport=StdioConfig(
                command="node",
                args=["test.js"],
            ),
        )

    async def test_create_health_monitor(self):
        """Test create_health_monitor convenience function."""
        config = self.create_test_server_config()

        async def quick_check():
            return True

        monitor = await create_health_monitor(
            config,
            health_check_function=quick_check,
            start=False,
        )

        assert monitor is not None
        assert monitor.server_name == "test-server"
        assert monitor.is_running is False

    async def test_check_server_health(self):
        """Test check_server_health convenience function."""
        registry = HealthMonitorRegistry()
        config = self.create_test_server_config("server1")

        async def healthy_check():
            return True

        await registry.register_monitor(
            config,
            health_check_function=healthy_check,
            start_immediately=False,
        )

        result = await check_server_health("server1", registry=registry)

        assert result is not None
        assert result.server_name == "server1"

    async def test_check_server_health_not_found(self):
        """Test checking health of non-existent server."""
        registry = HealthMonitorRegistry()

        result = await check_server_health("nonexistent", registry=registry)

        assert result is None

    async def test_global_registry(self):
        """Test global health monitor registry singleton."""
        registry1 = get_global_health_monitor_registry()
        registry2 = get_global_health_monitor_registry()

        # Should return same instance
        assert registry1 is registry2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
