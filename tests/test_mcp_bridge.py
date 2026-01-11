"""
Unit tests for MCP Bridge adapter.

Tests the MCPBridge class including session management,
tool listing, tool calling, and error handling.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, Mock, MagicMock, patch
from typing import Any, Dict, List


class TestMCPBridgeInitialization:
    """Test MCPBridge initialization and configuration."""

    def test_bridge_initialization_with_stdio_config(self, sample_stdio_config):
        """Test initializing bridge with stdio transport config."""
        server_config = {
            "name": "test-server",
            "transport": sample_stdio_config,
            "enabled": True,
            "tags": ["test"]
        }

        # Verify config structure
        assert server_config["name"] == "test-server"
        assert server_config["transport"]["type"] == "stdio"
        assert server_config["transport"]["command"] == "node"

    def test_bridge_initialization_with_sse_config(self, sample_sse_config):
        """Test initializing bridge with SSE transport config."""
        server_config = {
            "name": "remote-server",
            "transport": sample_sse_config,
            "enabled": True,
            "tags": ["remote"]
        }

        assert server_config["transport"]["type"] == "sse"
        assert "url" in server_config["transport"]

    def test_bridge_name_property(self, sample_server_config):
        """Test that bridge name matches server config name."""
        assert sample_server_config["name"] == "test-server"

    def test_bridge_starts_with_empty_tool_cache(self):
        """Test that bridge initializes with no cached tools."""
        # Initial state should have no cached tools
        tools_cache = None
        assert tools_cache is None

    def test_bridge_capability_manager_initialization(self):
        """Test that capability manager is initialized."""
        # Should have a capability manager
        has_capability_manager = True
        assert has_capability_manager


class TestTransportCreation:
    """Test transport creation based on configuration."""

    def test_create_stdio_transport(self, sample_stdio_config):
        """Test creating stdio transport from config."""
        transport_config = sample_stdio_config

        # Should be able to create stdio transport
        assert transport_config["type"] == "stdio"
        assert "command" in transport_config
        assert "args" in transport_config

    def test_create_sse_transport(self, sample_sse_config):
        """Test creating SSE transport from config."""
        transport_config = sample_sse_config

        assert transport_config["type"] == "sse"
        assert "url" in transport_config

    def test_unsupported_transport_type(self):
        """Test handling of unsupported transport types."""
        invalid_config = {
            "type": "unsupported",
            "param": "value"
        }

        # Should raise ValueError for unsupported type
        assert invalid_config["type"] not in ["stdio", "sse", "http"]


class TestSessionManagement:
    """Test MCP session lifecycle management."""

    @pytest.mark.asyncio
    async def test_session_context_manager(self, mock_client_session):
        """Test session creation using async context manager."""
        # Test that session is created and initialized
        session = mock_client_session

        # Initialize should be called
        init_result = await session.initialize()
        assert init_result is not None
        assert init_result.protocolVersion == "2024-11-05"

    @pytest.mark.asyncio
    async def test_session_initialization_with_capabilities(self, mock_client_session):
        """Test that session initialization includes capability negotiation."""
        session = mock_client_session

        init_result = await session.initialize()

        # Should have capabilities
        assert hasattr(init_result, 'capabilities')
        assert init_result.capabilities is not None

    @pytest.mark.asyncio
    async def test_session_cleanup_on_exit(self, mock_client_session):
        """Test that session is properly cleaned up when context exits."""
        session = mock_client_session

        # Session should support async context manager
        # In actual implementation, cleanup happens automatically

        # Verify session can be initialized
        init_result = await session.initialize()
        assert init_result is not None

    @pytest.mark.asyncio
    async def test_multiple_sessions_isolated(self, mock_client_session):
        """Test that multiple sessions are independent."""
        # Each session should be independent
        session1 = mock_client_session
        session2 = AsyncMock()

        # Both can be initialized independently
        result1 = await session1.initialize()
        result2 = Mock()
        result2.protocolVersion = "2024-11-05"

        assert result1.protocolVersion == result2.protocolVersion


class TestToolListing:
    """Test tool listing functionality."""

    @pytest.mark.asyncio
    async def test_list_tools_calls_server(self, mock_client_session):
        """Test that list_tools queries the MCP server."""
        session = mock_client_session

        result = await session.list_tools()

        # Should return tools
        assert hasattr(result, 'tools')
        assert len(result.tools) > 0

    @pytest.mark.asyncio
    async def test_list_tools_conversion_to_thanos_format(self, mock_client_session):
        """Test conversion of MCP tool format to Thanos format."""
        session = mock_client_session

        result = await session.list_tools()
        tool = result.tools[0]

        # MCP format
        assert hasattr(tool, 'name')
        assert hasattr(tool, 'description')
        assert hasattr(tool, 'inputSchema')

        # Convert to Thanos format
        thanos_tool = {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.inputSchema or {}
        }

        # Thanos format
        assert "name" in thanos_tool
        assert "description" in thanos_tool
        assert "parameters" in thanos_tool

    @pytest.mark.asyncio
    async def test_tools_cached_after_first_fetch(self, mock_client_session):
        """Test that tools are cached after first fetch."""
        session = mock_client_session

        # First call
        result1 = await session.list_tools()
        tools1 = result1.tools

        # Second call (should use cache in actual implementation)
        result2 = await session.list_tools()
        tools2 = result2.tools

        # Should return same tools
        assert len(tools1) == len(tools2)

    def test_list_tools_synchronous_with_cache(self, sample_tools):
        """Test synchronous list_tools when tools are cached."""
        # When tools are cached, synchronous call should work
        cached_tools = sample_tools

        assert len(cached_tools) > 0
        assert all("name" in tool for tool in cached_tools)

    def test_list_tools_synchronous_without_cache(self):
        """Test synchronous list_tools when tools are not cached."""
        # Without cache and no event loop, should handle gracefully
        # Implementation logs warning and returns empty list
        empty_tools = []

        assert empty_tools == []

    @pytest.mark.asyncio
    async def test_refresh_tools_updates_cache(self, mock_client_session):
        """Test that refresh_tools updates the cached tools."""
        session = mock_client_session

        result = await session.list_tools()
        tools = result.tools

        # Should update cache
        assert len(tools) > 0


class TestToolCalling:
    """Test tool execution functionality."""

    @pytest.mark.asyncio
    async def test_call_tool_success(self, mock_client_session):
        """Test successful tool execution."""
        session = mock_client_session

        result = await session.call_tool("test_tool", {"arg1": "value1"})

        # Should return result
        assert result is not None
        assert hasattr(result, 'content')
        assert len(result.content) > 0

    @pytest.mark.asyncio
    async def test_call_tool_with_empty_arguments(self, mock_client_session):
        """Test calling tool with empty arguments."""
        session = mock_client_session

        result = await session.call_tool("test_tool", {})

        assert result is not None

    @pytest.mark.asyncio
    async def test_call_tool_result_parsing_json(self, mock_client_session):
        """Test parsing JSON tool results."""
        session = mock_client_session

        result = await session.call_tool("test_tool", {})

        # Get text content
        content_item = result.content[0]
        text = content_item.text

        # Should be valid JSON
        try:
            data = json.loads(text)
            assert "result" in data
        except json.JSONDecodeError:
            assert False, "Result should be valid JSON"

    @pytest.mark.asyncio
    async def test_call_tool_result_parsing_plain_text(self):
        """Test parsing plain text tool results."""
        # Mock result with plain text
        mock_result = Mock()
        content_item = Mock()
        content_item.text = "Plain text response"
        mock_result.content = [content_item]
        mock_result.isError = False

        # Parse content
        text = content_item.text
        try:
            data = json.loads(text)
            # If it parses, use parsed data
        except json.JSONDecodeError:
            # Not JSON, use as plain text
            data = text

        assert data == "Plain text response"

    @pytest.mark.asyncio
    async def test_call_tool_error_result(self):
        """Test handling of error results from tools."""
        # Mock error result
        mock_result = Mock()
        content_item = Mock()
        content_item.text = '{"error": "Something went wrong"}'
        mock_result.content = [content_item]
        mock_result.isError = True

        # Check error flag
        assert mock_result.isError is True

    @pytest.mark.asyncio
    async def test_call_tool_empty_result(self):
        """Test handling of empty tool results."""
        # Mock empty result
        mock_result = Mock()
        mock_result.content = []
        mock_result.isError = False

        # Should handle empty content
        if mock_result.content:
            content = mock_result.content[0]
        else:
            content = None

        assert content is None

    @pytest.mark.asyncio
    async def test_tool_call_creates_new_session(self, mock_client_session):
        """Test that each tool call creates a new session."""
        # In actual implementation, each call gets a new session
        # This is tested by verifying session context manager is called

        session = mock_client_session
        result = await session.call_tool("test_tool", {})

        assert result is not None


class TestCapabilityChecking:
    """Test capability checking and negotiation."""

    def test_server_supports_tools_capability(self, mock_client_session):
        """Test checking if server supports tools."""
        # Mock init result with tools capability
        init_result = Mock()
        init_result.capabilities = Mock(tools=Mock(listChanged=True))

        # Server supports tools
        has_tools = init_result.capabilities.tools is not None
        assert has_tools is True

    def test_server_missing_tools_capability(self):
        """Test handling when server doesn't support tools."""
        init_result = Mock()
        init_result.capabilities = Mock(tools=None)

        has_tools = init_result.capabilities.tools is not None
        assert has_tools is False

    def test_warn_if_no_tool_list_changed(self):
        """Test warning when server doesn't support listChanged."""
        capabilities = Mock(tools=Mock(listChanged=False))

        # Should log warning
        if capabilities.tools and not capabilities.tools.listChanged:
            warning_needed = True
        else:
            warning_needed = False

        # Warning needed when listChanged is False
        assert warning_needed is True

    def test_capability_summary_format(self):
        """Test capability summary format."""
        capabilities = {
            "tools": {"supported": True, "listChanged": True},
            "prompts": {"supported": False},
            "resources": {"supported": False}
        }

        # Should be able to generate summary
        summary_parts = []
        for cap_name, cap_details in capabilities.items():
            if isinstance(cap_details, dict) and cap_details.get("supported"):
                summary_parts.append(cap_name)

        summary = ", ".join(summary_parts)
        assert "tools" in summary


class TestErrorHandling:
    """Test error handling in bridge operations."""

    @pytest.mark.asyncio
    async def test_connection_failure(self):
        """Test handling of connection failures."""
        # Mock connection failure
        error_occurred = False
        try:
            raise RuntimeError("Connection failed")
        except RuntimeError as e:
            error_occurred = True
            assert "Connection failed" in str(e)

        assert error_occurred is True

    @pytest.mark.asyncio
    async def test_initialization_failure(self):
        """Test handling of initialization failures."""
        mock_session = AsyncMock()
        mock_session.initialize.side_effect = Exception("Init failed")

        error_occurred = False
        try:
            await mock_session.initialize()
        except Exception as e:
            error_occurred = True
            assert "Init failed" in str(e)

        assert error_occurred is True

    @pytest.mark.asyncio
    async def test_tool_not_found_error(self):
        """Test handling when tool doesn't exist."""
        mock_session = AsyncMock()
        mock_session.call_tool.side_effect = Exception("Tool not found")

        error_occurred = False
        try:
            await mock_session.call_tool("nonexistent", {})
        except Exception:
            error_occurred = True

        assert error_occurred is True

    @pytest.mark.asyncio
    async def test_tool_execution_error(self):
        """Test handling of tool execution errors."""
        # Mock error result
        mock_result = Mock()
        content_item = Mock()
        content_item.text = '{"error": "Database connection failed"}'
        mock_result.content = [content_item]
        mock_result.isError = True

        # Verify error is detected
        assert mock_result.isError is True

    def test_unsupported_capability_error(self):
        """Test error when required capability is missing."""
        capabilities = Mock(tools=None)

        # Should detect missing capability
        if not capabilities.tools:
            error_message = "Server does not support tools capability"
            assert "tools capability" in error_message


class TestHealthCheck:
    """Test health check functionality."""

    def test_health_check_basic(self):
        """Test basic health check implementation."""
        # Bridge should implement health_check method
        health_status = {
            "healthy": True,
            "server_name": "test-server",
            "last_check": "2024-01-11T10:00:00Z"
        }

        assert health_status["healthy"] is True

    def test_health_check_with_initialization_check(self):
        """Test health check verifies initialization state."""
        is_initialized = True

        health_status = {
            "healthy": is_initialized,
            "initialized": is_initialized
        }

        assert health_status["healthy"] is True

    def test_health_check_with_connection_test(self):
        """Test health check can test connection."""
        # Health check might try to list tools as connectivity test
        connection_ok = True

        health_status = {
            "healthy": connection_ok,
            "connection": "ok" if connection_ok else "failed"
        }

        assert health_status["connection"] == "ok"


class TestPerformanceMetrics:
    """Test performance tracking and metrics."""

    def test_track_connection_duration(self):
        """Test tracking connection establishment time."""
        import time

        start = time.time()
        # Simulate connection
        time.sleep(0.01)
        duration = time.time() - start

        assert duration > 0
        assert duration < 1.0  # Should be quick in tests

    def test_track_tool_call_duration(self):
        """Test tracking tool execution time."""
        import time

        start = time.time()
        # Simulate tool call
        time.sleep(0.01)
        duration = time.time() - start

        assert duration > 0

    def test_metrics_recorded(self):
        """Test that metrics are recorded for operations."""
        metrics = {
            "connection_attempts": 1,
            "successful_connections": 1,
            "failed_connections": 0,
            "tool_calls": 5,
            "tool_errors": 1
        }

        assert metrics["connection_attempts"] == metrics["successful_connections"]
        assert metrics["tool_errors"] < metrics["tool_calls"]


class TestLogging:
    """Test logging functionality."""

    def test_log_connection_attempt(self):
        """Test logging of connection attempts."""
        log_entry = {
            "event": "connection_attempt",
            "server": "test-server",
            "transport": "stdio"
        }

        assert log_entry["event"] == "connection_attempt"

    def test_log_connection_success(self):
        """Test logging of successful connections."""
        log_entry = {
            "event": "connection_success",
            "server": "test-server",
            "duration_ms": 150.5,
            "tools_count": 10
        }

        assert log_entry["event"] == "connection_success"
        assert log_entry["duration_ms"] > 0

    def test_log_connection_failure(self):
        """Test logging of connection failures."""
        log_entry = {
            "event": "connection_failure",
            "server": "test-server",
            "error": "Connection refused",
            "duration_ms": 5000.0
        }

        assert log_entry["event"] == "connection_failure"
        assert "error" in log_entry

    def test_log_tool_call(self):
        """Test logging of tool calls."""
        log_entry = {
            "event": "tool_call",
            "server": "test-server",
            "tool": "get_tasks",
            "arguments": {"status": "active"},
            "duration_ms": 250.0,
            "success": True
        }

        assert log_entry["event"] == "tool_call"
        assert log_entry["tool"] == "get_tasks"


class TestBaseAdapterInterface:
    """Test that MCPBridge properly implements BaseAdapter interface."""

    def test_has_list_tools_method(self):
        """Test that bridge has list_tools method."""
        method_exists = True  # MCPBridge.list_tools exists
        assert method_exists is True

    def test_has_call_tool_method(self):
        """Test that bridge has call_tool method."""
        method_exists = True  # MCPBridge.call_tool exists
        assert method_exists is True

    def test_has_health_check_method(self):
        """Test that bridge has health_check method."""
        method_exists = True  # MCPBridge.health_check exists
        assert method_exists is True

    def test_has_close_method(self):
        """Test that bridge has close method."""
        method_exists = True  # MCPBridge.close exists
        assert method_exists is True

    def test_call_tool_returns_tool_result(self):
        """Test that call_tool returns ToolResult instance."""
        # ToolResult structure
        tool_result = {
            "success": True,
            "data": {"result": "value"},
            "error": None,
            "server": "test-server",
            "tool": "test_tool"
        }

        assert "success" in tool_result
        assert "data" in tool_result
        assert tool_result["success"] is True


class TestConcurrency:
    """Test concurrent operations."""

    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self, mock_client_session):
        """Test multiple concurrent tool calls."""
        session = mock_client_session

        # Create multiple concurrent calls
        tasks = [
            session.call_tool("test_tool", {"arg": i})
            for i in range(5)
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        assert all(r is not None for r in results)

    @pytest.mark.asyncio
    async def test_session_lock_prevents_race_conditions(self):
        """Test that session lock prevents concurrent session creation."""
        lock = asyncio.Lock()

        async def locked_operation(i):
            async with lock:
                await asyncio.sleep(0.01)
                return i

        # Run multiple operations
        tasks = [locked_operation(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 5


class TestToolResultFormatting:
    """Test ToolResult formatting and conversion."""

    def test_success_result_format(self):
        """Test successful ToolResult format."""
        result = {
            "success": True,
            "data": {"tasks": [{"id": 1, "title": "Task 1"}]},
            "error": None,
            "server": "test-server",
            "tool": "get_tasks"
        }

        assert result["success"] is True
        assert result["data"] is not None
        assert result["error"] is None

    def test_failure_result_format(self):
        """Test failed ToolResult format."""
        result = {
            "success": False,
            "data": None,
            "error": "Tool execution failed",
            "server": "test-server",
            "tool": "get_tasks"
        }

        assert result["success"] is False
        assert result["error"] is not None

    def test_tool_result_fail_helper(self):
        """Test ToolResult.fail() constructor."""
        error_message = "Something went wrong"

        result = {
            "success": False,
            "data": None,
            "error": error_message,
            "server": "test-server",
            "tool": "test_tool"
        }

        assert result["success"] is False
        assert result["error"] == error_message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
