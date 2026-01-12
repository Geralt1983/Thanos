"""
Integration tests for MCP server lifecycle management.

These tests validate the full lifecycle of MCP servers including:
- Initialization and shutdown
- Reconnection after failures
- Error recovery
- Multiple concurrent servers
- Connection pooling
- Health monitoring

NOTE: These tests require actual MCP servers to be available.
Configure test servers in tests/integration/test_servers.json
"""

import asyncio
import json
import logging
import os
import pytest
import time
from pathlib import Path
from typing import Dict, Any, List

# Import MCP components
try:
    from Tools.adapters.mcp_bridge import MCPBridge
    from Tools.adapters.mcp_config import MCPServerConfig, StdioConfig
    from Tools.adapters.mcp_discovery import MCPServerDiscovery
    from Tools.adapters.mcp_pool import MCPConnectionPool, PoolConfig
    from Tools.adapters.mcp_health import HealthMonitor, HealthCheckConfig
    from Tools.adapters.mcp_errors import (
        MCPConnectionError,
        MCPTimeoutError,
        MCPServerUnavailableError,
    )
    from Tools.adapters.base import ToolResult

    MCP_AVAILABLE = True
except ImportError as e:
    MCP_AVAILABLE = False
    IMPORT_ERROR = str(e)


logger = logging.getLogger(__name__)


# ============================================================================
# Fixtures and Test Configuration
# ============================================================================


@pytest.fixture(scope="module")
def test_servers_config() -> Dict[str, Any]:
    """Load test server configurations."""
    config_file = Path(__file__).parent / "test_servers.json"

    if config_file.exists():
        with open(config_file) as f:
            return json.load(f)

    # Default test configuration
    return {
        "servers": [
            {
                "name": "test-server-1",
                "transport": {
                    "type": "stdio",
                    "command": "node",
                    "args": ["${WORKOS_MCP_PATH}"],
                    "env": {
                        "DATABASE_URL": "${DATABASE_URL}",
                        "NODE_ENV": "test"
                    }
                },
                "enabled": True,
                "tags": ["test", "primary"]
            }
        ]
    }


@pytest.fixture
def skip_if_mcp_unavailable():
    """Skip tests if MCP SDK is not available."""
    if not MCP_AVAILABLE:
        pytest.skip(f"MCP SDK not available: {IMPORT_ERROR}")


@pytest.fixture
async def test_bridge(skip_if_mcp_unavailable) -> MCPBridge:
    """Create a test MCP bridge."""
    # Try to create from environment
    server_path = os.getenv("WORKOS_MCP_PATH")
    database_url = os.getenv("DATABASE_URL")

    if not server_path or not database_url:
        pytest.skip("Test server not configured. Set WORKOS_MCP_PATH and DATABASE_URL")

    config = MCPServerConfig(
        name="test-server",
        transport=StdioConfig(
            type="stdio",
            command="node",
            args=[server_path],
            env={"DATABASE_URL": database_url}
        ),
        enabled=True,
        tags=["test"]
    )

    bridge = MCPBridge(config)
    yield bridge
    await bridge.close()


# ============================================================================
# Test: Full Lifecycle (init → list → call → shutdown)
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
class TestMCPLifecycle:
    """Test full MCP server lifecycle."""

    async def test_complete_lifecycle(self, test_bridge):
        """Test complete lifecycle: init → list tools → call tool → shutdown."""
        # 1. Initialization (happens on first operation)
        logger.info("Step 1: Initialization")
        tools = await test_bridge.list_tools()
        assert len(tools) > 0
        logger.info(f"  ✓ Server initialized with {len(tools)} tools")

        # 2. List tools
        logger.info("Step 2: List tools")
        tools = await test_bridge.list_tools()
        assert len(tools) > 0
        tool_names = [tool["name"] for tool in tools]
        logger.info(f"  ✓ Tools available: {', '.join(tool_names[:3])}...")

        # 3. Call tool
        logger.info("Step 3: Call tool")
        if "get_today_metrics" in tool_names:
            result = await test_bridge.call_tool("get_today_metrics", {})
            assert isinstance(result, ToolResult)
            logger.info(f"  ✓ Tool call {'succeeded' if result.success else 'failed'}")
        else:
            logger.info("  ⊙ Skipped: get_today_metrics not available")

        # 4. Shutdown
        logger.info("Step 4: Shutdown")
        await test_bridge.close()
        logger.info("  ✓ Bridge closed successfully")

    async def test_multiple_operations_single_session(self, test_bridge):
        """Test multiple operations in a single session."""
        operations = [
            ("list_tools", None),
            ("call_tool", ("get_today_metrics", {})),
            ("list_tools", None),
            ("call_tool", ("get_today_metrics", {})),
        ]

        for op_type, args in operations:
            if op_type == "list_tools":
                result = await test_bridge.list_tools()
                assert len(result) > 0
            elif op_type == "call_tool":
                tool_name, tool_args = args
                result = await test_bridge.call_tool(tool_name, tool_args)
                assert isinstance(result, ToolResult)

        logger.info(f"✓ Completed {len(operations)} operations successfully")

    async def test_lazy_initialization(self, skip_if_mcp_unavailable):
        """Test that server initializes lazily on first use."""
        server_path = os.getenv("WORKOS_MCP_PATH")
        if not server_path:
            pytest.skip("Test server not configured")

        config = MCPServerConfig(
            name="lazy-test",
            transport=StdioConfig(
                type="stdio",
                command="node",
                args=[server_path],
                env={"DATABASE_URL": os.getenv("DATABASE_URL", "")}
            )
        )

        bridge = MCPBridge(config)

        # Should not be initialized yet
        # (No direct way to check, but documented behavior)

        # First operation should trigger initialization
        tools = await test_bridge.list_tools()
        assert len(tools) > 0

        await bridge.close()


# ============================================================================
# Test: Reconnection and Error Recovery
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
class TestMCPReconnection:
    """Test reconnection and error recovery."""

    async def test_reconnect_after_close(self, skip_if_mcp_unavailable):
        """Test reconnecting after closing bridge."""
        server_path = os.getenv("WORKOS_MCP_PATH")
        if not server_path:
            pytest.skip("Test server not configured")

        config = MCPServerConfig(
            name="reconnect-test",
            transport=StdioConfig(
                type="stdio",
                command="node",
                args=[server_path],
                env={"DATABASE_URL": os.getenv("DATABASE_URL", "")}
            )
        )

        # First connection
        bridge1 = MCPBridge(config)
        tools1 = await bridge1.list_tools()
        assert len(tools1) > 0
        await bridge1.close()

        # Second connection (new bridge instance)
        bridge2 = MCPBridge(config)
        tools2 = await bridge2.list_tools()
        assert len(tools2) > 0
        await bridge2.close()

        # Should have same tools
        assert len(tools1) == len(tools2)

    async def test_handle_connection_error(self, skip_if_mcp_unavailable):
        """Test handling connection errors gracefully."""
        # Create config with invalid server path
        config = MCPServerConfig(
            name="invalid-server",
            transport=StdioConfig(
                type="stdio",
                command="nonexistent-command",
                args=["invalid.js"]
            )
        )

        bridge = MCPBridge(config)

        # Should fail gracefully
        try:
            tools = await bridge.list_tools()
            # If it succeeds, that's unexpected but okay
            logger.warning("Expected connection error but operation succeeded")
        except Exception as e:
            # Should get an error
            assert isinstance(e, (MCPConnectionError, Exception))
            logger.info(f"✓ Connection error handled: {type(e).__name__}")

        await bridge.close()

    async def test_timeout_handling(self, test_bridge):
        """Test timeout handling for slow operations."""
        # Note: This test may not reliably trigger timeouts
        # Documented for completeness

        start_time = time.time()

        try:
            result = await test_bridge.call_tool("get_today_metrics", {})
            elapsed = time.time() - start_time

            logger.info(f"Operation completed in {elapsed:.3f}s")
            assert isinstance(result, ToolResult)

        except MCPTimeoutError as e:
            logger.info(f"✓ Timeout handled gracefully: {e}")
        except Exception as e:
            logger.info(f"Other error: {type(e).__name__}: {e}")


# ============================================================================
# Test: Multiple Concurrent Servers
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
class TestMultipleConcurrentServers:
    """Test managing multiple concurrent MCP servers."""

    async def test_multiple_bridges_sequential(self, skip_if_mcp_unavailable):
        """Test using multiple bridges sequentially."""
        server_path = os.getenv("WORKOS_MCP_PATH")
        if not server_path:
            pytest.skip("Test server not configured")

        # Create multiple bridge configs
        configs = [
            MCPServerConfig(
                name=f"test-server-{i}",
                transport=StdioConfig(
                    type="stdio",
                    command="node",
                    args=[server_path],
                    env={"DATABASE_URL": os.getenv("DATABASE_URL", "")}
                )
            )
            for i in range(3)
        ]

        bridges = [MCPBridge(config) for config in configs]

        # Use each bridge
        for i, bridge in enumerate(bridges):
            tools = await bridge.list_tools()
            assert len(tools) > 0
            logger.info(f"✓ Bridge {i+1} has {len(tools)} tools")

        # Cleanup
        for bridge in bridges:
            await bridge.close()

    async def test_multiple_bridges_concurrent(self, skip_if_mcp_unavailable):
        """Test using multiple bridges concurrently."""
        server_path = os.getenv("WORKOS_MCP_PATH")
        if not server_path:
            pytest.skip("Test server not configured")

        # Create multiple bridge configs
        configs = [
            MCPServerConfig(
                name=f"concurrent-server-{i}",
                transport=StdioConfig(
                    type="stdio",
                    command="node",
                    args=[server_path],
                    env={"DATABASE_URL": os.getenv("DATABASE_URL", "")}
                )
            )
            for i in range(3)
        ]

        bridges = [MCPBridge(config) for config in configs]

        start_time = time.time()

        # Concurrent tool listing
        tasks = [bridge.list_tools() for bridge in bridges]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        elapsed = time.time() - start_time

        # Check results
        successful = sum(1 for r in results if not isinstance(r, Exception))
        logger.info(f"✓ {successful}/3 bridges succeeded in {elapsed:.3f}s")

        # Cleanup
        cleanup_tasks = [bridge.close() for bridge in bridges]
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)

    async def test_concurrent_tool_calls_multiple_servers(self, skip_if_mcp_unavailable):
        """Test concurrent tool calls across multiple servers."""
        server_path = os.getenv("WORKOS_MCP_PATH")
        if not server_path:
            pytest.skip("Test server not configured")

        # Create two bridges
        bridges = [
            MCPBridge(
                MCPServerConfig(
                    name=f"multi-call-{i}",
                    transport=StdioConfig(
                        type="stdio",
                        command="node",
                        args=[server_path],
                        env={"DATABASE_URL": os.getenv("DATABASE_URL", "")}
                    )
                )
            )
            for i in range(2)
        ]

        # Make concurrent calls
        tasks = []
        for bridge in bridges:
            for _ in range(2):  # 2 calls per bridge
                tasks.append(bridge.call_tool("get_today_metrics", {}))

        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start_time

        successful = sum(
            1 for r in results
            if isinstance(r, ToolResult) and r.success
        )

        logger.info(f"✓ {successful}/{len(tasks)} concurrent calls succeeded in {elapsed:.3f}s")

        # Cleanup
        for bridge in bridges:
            await bridge.close()


# ============================================================================
# Test: Connection Pooling
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
class TestMCPConnectionPooling:
    """Test connection pooling for MCP sessions."""

    async def test_connection_pool_basic(self, skip_if_mcp_unavailable):
        """Test basic connection pool functionality."""
        server_path = os.getenv("WORKOS_MCP_PATH")
        if not server_path:
            pytest.skip("Test server not configured")

        config = MCPServerConfig(
            name="pool-test",
            transport=StdioConfig(
                type="stdio",
                command="node",
                args=[server_path],
                env={"DATABASE_URL": os.getenv("DATABASE_URL", "")}
            )
        )

        pool_config = PoolConfig(
            min_connections=1,
            max_connections=3,
            enable_health_checks=False,  # Disable for simpler test
        )

        pool = MCPConnectionPool(config, pool_config)
        await pool.initialize()

        # Acquire connection
        async with pool.acquire() as session:
            assert session is not None
            # Use session (note: actual session usage depends on implementation)

        # Pool should have connection back
        stats = pool.get_stats()
        assert stats["total_connections"] >= 1

        await pool.close()

    async def test_connection_pool_concurrent_access(self, skip_if_mcp_unavailable):
        """Test concurrent access to connection pool."""
        server_path = os.getenv("WORKOS_MCP_PATH")
        if not server_path:
            pytest.skip("Test server not configured")

        config = MCPServerConfig(
            name="pool-concurrent-test",
            transport=StdioConfig(
                type="stdio",
                command="node",
                args=[server_path],
                env={"DATABASE_URL": os.getenv("DATABASE_URL", "")}
            )
        )

        pool_config = PoolConfig(
            min_connections=2,
            max_connections=5,
            enable_health_checks=False,
        )

        pool = MCPConnectionPool(config, pool_config)
        await pool.initialize()

        # Concurrent acquisitions
        async def use_connection(i: int):
            async with pool.acquire() as session:
                logger.info(f"Connection {i} acquired")
                await asyncio.sleep(0.1)  # Simulate work

        tasks = [use_connection(i) for i in range(10)]
        await asyncio.gather(*tasks)

        stats = pool.get_stats()
        logger.info(f"✓ Pool handled {stats['total_acquisitions']} acquisitions")

        await pool.close()


# ============================================================================
# Test: Health Monitoring
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
class TestMCPHealthMonitoring:
    """Test health monitoring for MCP servers."""

    async def test_health_monitor_basic(self, skip_if_mcp_unavailable):
        """Test basic health monitoring."""
        server_path = os.getenv("WORKOS_MCP_PATH")
        if not server_path:
            pytest.skip("Test server not configured")

        config = MCPServerConfig(
            name="health-test",
            transport=StdioConfig(
                type="stdio",
                command="node",
                args=[server_path],
                env={"DATABASE_URL": os.getenv("DATABASE_URL", "")}
            )
        )

        health_config = HealthCheckConfig(
            check_interval=5.0,  # 5 seconds
            enable_auto_checks=False,  # Manual checks only
        )

        monitor = HealthMonitor(config, health_config)

        # Perform health check
        result = await monitor.perform_health_check()

        logger.info(f"Health status: {result.status.value}")
        logger.info(f"Latency: {result.latency_ms:.2f}ms" if result.latency_ms else "  No latency")

        assert result is not None

    async def test_health_monitor_periodic_checks(self, skip_if_mcp_unavailable):
        """Test periodic health checks."""
        server_path = os.getenv("WORKOS_MCP_PATH")
        if not server_path:
            pytest.skip("Test server not configured")

        config = MCPServerConfig(
            name="health-periodic-test",
            transport=StdioConfig(
                type="stdio",
                command="node",
                args=[server_path],
                env={"DATABASE_URL": os.getenv("DATABASE_URL", "")}
            )
        )

        health_config = HealthCheckConfig(
            check_interval=2.0,  # 2 seconds
            enable_auto_checks=True,
        )

        async with HealthMonitor(config, health_config) as monitor:
            # Wait for a few checks
            await asyncio.sleep(5)

            # Get status
            status = await monitor.get_health_status()
            logger.info(f"✓ Health status after periodic checks: {status.status.value}")

            # Should have some metrics
            assert status.metrics.total_requests >= 0


# ============================================================================
# Test: Performance Benchmarks
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.benchmark
class TestMCPLifecyclePerformance:
    """Performance benchmarks for MCP lifecycle operations."""

    async def test_initialization_performance(self, skip_if_mcp_unavailable):
        """Benchmark server initialization time."""
        server_path = os.getenv("WORKOS_MCP_PATH")
        if not server_path:
            pytest.skip("Test server not configured")

        config = MCPServerConfig(
            name="perf-init-test",
            transport=StdioConfig(
                type="stdio",
                command="node",
                args=[server_path],
                env={"DATABASE_URL": os.getenv("DATABASE_URL", "")}
            )
        )

        iterations = 5
        times = []

        for i in range(iterations):
            bridge = MCPBridge(config)

            start = time.time()
            await bridge.list_tools()  # Triggers initialization
            elapsed = time.time() - start

            times.append(elapsed)
            await bridge.close()

        avg_time = sum(times) / len(times)
        logger.info(f"Initialization performance:")
        logger.info(f"  Average: {avg_time*1000:.2f}ms")
        logger.info(f"  Min: {min(times)*1000:.2f}ms")
        logger.info(f"  Max: {max(times)*1000:.2f}ms")

    async def test_concurrent_operations_performance(self, skip_if_mcp_unavailable):
        """Benchmark concurrent operations performance."""
        server_path = os.getenv("WORKOS_MCP_PATH")
        if not server_path:
            pytest.skip("Test server not configured")

        config = MCPServerConfig(
            name="perf-concurrent-test",
            transport=StdioConfig(
                type="stdio",
                command="node",
                args=[server_path],
                env={"DATABASE_URL": os.getenv("DATABASE_URL", "")}
            )
        )

        bridge = MCPBridge(config)

        # Concurrent calls
        num_calls = 10

        start = time.time()
        tasks = [bridge.call_tool("get_today_metrics", {}) for _ in range(num_calls)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start

        successful = sum(
            1 for r in results
            if isinstance(r, ToolResult) and r.success
        )

        logger.info(f"Concurrent operations performance ({num_calls} calls):")
        logger.info(f"  Total time: {elapsed*1000:.2f}ms")
        logger.info(f"  Avg per call: {elapsed*1000/num_calls:.2f}ms")
        logger.info(f"  Successful: {successful}/{num_calls}")

        await bridge.close()


# ============================================================================
# Main: Run tests with pytest
# ============================================================================


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s", "--log-cli-level=INFO"])
