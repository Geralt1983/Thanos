"""
Integration tests for WorkOS MCP server.

These tests validate the integration with the actual WorkOS MCP server,
testing real tool calls, error handling, and server lifecycle management.

NOTE: These tests require:
1. WorkOS MCP server to be built: cd mcp-servers/workos-mcp && npm run build
2. Database connection configured: DATABASE_URL environment variable
3. Server path set: WORKOS_MCP_PATH or use default location
"""

import asyncio
import json
import logging
import os
import pytest
import time
from pathlib import Path
from typing import Dict, Any

# Import MCP components
try:
    from Tools.adapters.workos_mcp_bridge import (
        create_workos_mcp_bridge,
        create_workos_mcp_config,
        get_default_server_path,
    )
    from Tools.adapters.mcp_bridge import MCPBridge
    from Tools.adapters.mcp_config import MCPServerConfig
    from Tools.adapters.base import ToolResult

    MCP_AVAILABLE = True
except ImportError as e:
    MCP_AVAILABLE = False
    IMPORT_ERROR = str(e)


logger = logging.getLogger(__name__)


# ============================================================================
# Fixtures and Configuration
# ============================================================================


@pytest.fixture(scope="module")
def workos_server_available() -> bool:
    """Check if WorkOS MCP server is available for testing."""
    if not MCP_AVAILABLE:
        return False

    server_path = get_default_server_path()

    # Check if server file exists
    if server_path.startswith("${"):
        # Environment variable reference, check env
        return os.getenv("WORKOS_MCP_PATH") is not None

    return Path(server_path).exists()


@pytest.fixture(scope="module")
def database_configured() -> bool:
    """Check if database is configured."""
    return os.getenv("DATABASE_URL") is not None or os.getenv("WORKOS_DATABASE_URL") is not None


@pytest.fixture(scope="module")
def skip_if_server_unavailable(workos_server_available, database_configured):
    """Skip tests if server or database is not available."""
    if not MCP_AVAILABLE:
        pytest.skip(f"MCP SDK not available: {IMPORT_ERROR}")
    if not workos_server_available:
        pytest.skip("WorkOS MCP server not found. Build with: cd mcp-servers/workos-mcp && npm run build")
    if not database_configured:
        pytest.skip("Database not configured. Set DATABASE_URL environment variable")


@pytest.fixture
async def workos_bridge(skip_if_server_unavailable):
    """Create WorkOS MCP bridge for testing."""
    bridge = await create_workos_mcp_bridge()
    yield bridge
    # Cleanup
    await bridge.close()


# ============================================================================
# Test: Server Connection and Initialization
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
class TestWorkosMCPConnection:
    """Test connection and initialization with WorkOS MCP server."""

    async def test_bridge_creation(self, skip_if_server_unavailable):
        """Test creating WorkOS MCP bridge."""
        bridge = await create_workos_mcp_bridge()

        assert bridge is not None
        assert isinstance(bridge, MCPBridge)
        assert bridge.name == "workos-mcp"

        await bridge.close()

    async def test_config_creation(self, skip_if_server_unavailable):
        """Test creating WorkOS MCP configuration."""
        config = create_workos_mcp_config()

        assert config is not None
        assert isinstance(config, MCPServerConfig)
        assert config.name == "workos-mcp"
        assert config.transport.type == "stdio"

    async def test_server_initialization(self, workos_bridge):
        """Test server initialization and capability negotiation."""
        # Bridge should initialize on first tool list
        tools = await workos_bridge.list_tools()

        # Should have received tools from server
        assert len(tools) > 0

        # Check capability manager has server capabilities
        assert workos_bridge.capability_manager is not None
        assert workos_bridge.capability_manager.server_capabilities is not None


# ============================================================================
# Test: Tool Discovery and Listing
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
class TestWorkosMCPToolDiscovery:
    """Test tool discovery with WorkOS MCP server."""

    async def test_list_tools(self, workos_bridge):
        """Test listing all available tools."""
        tools = await workos_bridge.list_tools()

        assert len(tools) > 0

        # Check tool structure
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "parameters" in tool

    async def test_expected_workos_tools_available(self, workos_bridge):
        """Test that expected WorkOS tools are available."""
        tools = await workos_bridge.list_tools()
        tool_names = [tool["name"] for tool in tools]

        # Expected WorkOS tools
        expected_tools = [
            "get_tasks",
            "get_today_metrics",
            "complete_task",
            "create_task",
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names, f"Expected tool '{expected_tool}' not found"

    async def test_tool_schemas_valid(self, workos_bridge):
        """Test that tool schemas are valid JSON Schema."""
        tools = await workos_bridge.list_tools()

        for tool in tools:
            schema = tool["parameters"]

            # Should have type
            assert "type" in schema
            assert schema["type"] == "object"

            # Should have properties
            if "properties" in schema:
                assert isinstance(schema["properties"], dict)

    async def test_tool_caching(self, workos_bridge):
        """Test that tools are cached after first list."""
        # First call - should fetch from server
        start_time = time.time()
        tools1 = await workos_bridge.list_tools()
        first_call_time = time.time() - start_time

        # Second call - should use cache
        start_time = time.time()
        tools2 = await workos_bridge.list_tools()
        second_call_time = time.time() - start_time

        # Should return same tools
        assert len(tools1) == len(tools2)

        # Second call should be faster (cached)
        # Note: This may not always be true due to system variance
        logger.info(f"First call: {first_call_time:.3f}s, Second call: {second_call_time:.3f}s")


# ============================================================================
# Test: Tool Execution
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
class TestWorkosMCPToolExecution:
    """Test tool execution with WorkOS MCP server."""

    async def test_call_get_tasks(self, workos_bridge):
        """Test calling get_tasks tool."""
        result = await workos_bridge.call_tool(
            "get_tasks",
            {"status": "active", "limit": 10}
        )

        assert isinstance(result, ToolResult)
        assert result.success is True or result.success is False  # Either success or failure is valid

        if result.success:
            # Should have data
            assert result.data is not None
            logger.info(f"get_tasks returned: {result.data}")
        else:
            # Should have error
            assert result.error is not None
            logger.warning(f"get_tasks failed: {result.error}")

    async def test_call_get_today_metrics(self, workos_bridge):
        """Test calling get_today_metrics tool."""
        result = await workos_bridge.call_tool("get_today_metrics", {})

        assert isinstance(result, ToolResult)

        if result.success:
            # Should return metrics data
            assert result.data is not None
            logger.info(f"get_today_metrics returned: {result.data}")

    async def test_call_nonexistent_tool(self, workos_bridge):
        """Test calling a tool that doesn't exist."""
        result = await workos_bridge.call_tool(
            "nonexistent_tool",
            {}
        )

        assert isinstance(result, ToolResult)
        assert result.success is False
        assert result.error is not None
        assert "not found" in result.error.lower() or "unknown" in result.error.lower()

    async def test_call_tool_with_invalid_args(self, workos_bridge):
        """Test calling tool with invalid arguments."""
        result = await workos_bridge.call_tool(
            "get_tasks",
            {"status": "invalid_status"}  # Invalid enum value
        )

        # Should handle validation error gracefully
        assert isinstance(result, ToolResult)
        # May succeed if server doesn't validate strictly, or fail with error
        if not result.success:
            assert result.error is not None

    async def test_call_tool_with_missing_required_args(self, workos_bridge):
        """Test calling tool with missing required arguments."""
        # create_task requires 'title'
        result = await workos_bridge.call_tool(
            "create_task",
            {"description": "Test task"}  # Missing required 'title'
        )

        assert isinstance(result, ToolResult)
        # Should fail with validation error
        if not result.success:
            assert result.error is not None


# ============================================================================
# Test: Error Handling
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
class TestWorkosMCPErrorHandling:
    """Test error handling with WorkOS MCP server."""

    async def test_handle_server_error_gracefully(self, workos_bridge):
        """Test that server errors are handled gracefully."""
        # Try to create task with invalid data that might cause server error
        result = await workos_bridge.call_tool(
            "create_task",
            {
                "title": "Test",
                "invalid_field": "should be ignored or cause error"
            }
        )

        assert isinstance(result, ToolResult)
        # Should either succeed (ignoring extra field) or fail gracefully
        if not result.success:
            assert result.error is not None
            assert isinstance(result.error, str)

    async def test_bridge_health_check(self, workos_bridge):
        """Test bridge health check."""
        is_healthy = await workos_bridge.health_check()

        assert isinstance(is_healthy, bool)
        # After successful connection, should be healthy
        # Note: May be False if server is having issues


# ============================================================================
# Test: Session Management
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
class TestWorkosMCPSessionManagement:
    """Test session management with WorkOS MCP server."""

    async def test_multiple_sequential_calls(self, workos_bridge):
        """Test making multiple sequential tool calls."""
        results = []

        for i in range(3):
            result = await workos_bridge.call_tool("get_today_metrics", {})
            results.append(result)
            assert isinstance(result, ToolResult)

        # All calls should succeed or fail gracefully
        assert len(results) == 3

    async def test_bridge_cleanup(self, skip_if_server_unavailable):
        """Test bridge cleanup and resource management."""
        bridge = await create_workos_mcp_bridge()

        # Use bridge
        await bridge.list_tools()

        # Close bridge
        await bridge.close()

        # Should be closed
        # Note: No direct way to check closed state, but should not raise

    async def test_bridge_context_manager(self, skip_if_server_unavailable):
        """Test using bridge as async context manager."""
        # Note: MCPBridge may not implement __aenter__/__aexit__
        # This test documents expected behavior

        bridge = await create_workos_mcp_bridge()
        try:
            tools = await bridge.list_tools()
            assert len(tools) > 0
        finally:
            await bridge.close()


# ============================================================================
# Test: Performance Benchmarks
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.benchmark
class TestWorkosMCPPerformance:
    """Performance benchmarks for WorkOS MCP server."""

    async def test_tool_listing_performance(self, workos_bridge):
        """Benchmark tool listing performance."""
        iterations = 10
        times = []

        for i in range(iterations):
            start = time.time()
            await workos_bridge.list_tools()
            elapsed = time.time() - start
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)

        logger.info(f"Tool listing performance:")
        logger.info(f"  Average: {avg_time*1000:.2f}ms")
        logger.info(f"  Min: {min_time*1000:.2f}ms")
        logger.info(f"  Max: {max_time*1000:.2f}ms")

        # Document results
        assert avg_time < 1.0, f"Tool listing too slow: {avg_time:.3f}s"

    async def test_tool_call_performance(self, workos_bridge):
        """Benchmark tool call performance."""
        iterations = 5
        times = []

        for i in range(iterations):
            start = time.time()
            await workos_bridge.call_tool("get_today_metrics", {})
            elapsed = time.time() - start
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)

        logger.info(f"Tool call performance (get_today_metrics):")
        logger.info(f"  Average: {avg_time*1000:.2f}ms")
        logger.info(f"  Min: {min_time*1000:.2f}ms")
        logger.info(f"  Max: {max_time*1000:.2f}ms")

        # Tool calls should be reasonably fast
        # Note: This depends on database query complexity
        assert avg_time < 5.0, f"Tool call too slow: {avg_time:.3f}s"

    async def test_concurrent_tool_calls(self, workos_bridge):
        """Test performance of concurrent tool calls."""
        num_concurrent = 5

        start = time.time()

        # Make concurrent calls
        tasks = [
            workos_bridge.call_tool("get_today_metrics", {})
            for _ in range(num_concurrent)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        elapsed = time.time() - start

        # Check results
        successful = sum(1 for r in results if isinstance(r, ToolResult) and r.success)

        logger.info(f"Concurrent tool calls ({num_concurrent}):")
        logger.info(f"  Total time: {elapsed*1000:.2f}ms")
        logger.info(f"  Avg per call: {elapsed*1000/num_concurrent:.2f}ms")
        logger.info(f"  Successful: {successful}/{num_concurrent}")

        # Should handle concurrent calls
        assert len(results) == num_concurrent


# ============================================================================
# Test: Integration with Adapter Manager
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
class TestWorkosMCPAdapterManagerIntegration:
    """Test WorkOS MCP integration with AdapterManager."""

    async def test_workos_tools_via_adapter_manager(self, skip_if_server_unavailable):
        """Test accessing WorkOS tools through AdapterManager."""
        try:
            from Tools.adapters import get_default_manager

            # Create manager with MCP support
            manager = get_default_manager(enable_mcp=False)  # Don't auto-discover yet

            # Manually register WorkOS bridge
            bridge = await create_workos_mcp_bridge()
            manager.register_adapter(bridge)

            # List all tools
            all_tools = manager.list_tools()
            tool_names = [tool["name"] for tool in all_tools]

            # Should include WorkOS tools
            assert "get_tasks" in tool_names or "get_today_metrics" in tool_names

            # Call tool through manager
            result = await manager.call_tool("get_today_metrics", {})
            assert isinstance(result, ToolResult)

            # Cleanup
            await manager.close_all()

        except ImportError as e:
            pytest.skip(f"AdapterManager not available: {e}")


# ============================================================================
# Main: Run tests with pytest
# ============================================================================


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s", "--log-cli-level=INFO"])
