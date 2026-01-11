"""
Unit tests for MCPBridge component.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from Tools.adapters.base import ToolResult


@pytest.mark.asyncio
class TestMCPBridge:
    """Test MCPBridge functionality."""

    async def test_initialization(self, mock_server_config):
        """Test MCPBridge initialization."""
        from Tools.adapters.mcp_bridge import MCPBridge

        bridge = MCPBridge(mock_server_config)

        assert bridge.name == "test-server"
        assert bridge.config == mock_server_config
        assert not bridge._connected

    async def test_list_tools_before_connect(self, mock_server_config):
        """Test list_tools before connection."""
        from Tools.adapters.mcp_bridge import MCPBridge

        bridge = MCPBridge(mock_server_config)

        tools = bridge.list_tools()
        assert tools == []

    @patch("Tools.adapters.mcp_bridge.StdioServerParameters")
    @patch("Tools.adapters.mcp_bridge.stdio_client")
    async def test_connect(self, mock_stdio, mock_params, mock_server_config, mock_mcp_client):
        """Test connection to MCP server."""
        from Tools.adapters.mcp_bridge import MCPBridge

        mock_stdio.return_value.__aenter__.return_value = (
            AsyncMock(), AsyncMock()
        )

        bridge = MCPBridge(mock_server_config)

        with patch.object(bridge, "_client", mock_mcp_client):
            await bridge.connect()

            assert bridge._connected
            mock_mcp_client.list_tools.assert_called_once()

    async def test_list_tools_after_connect(self, mock_server_config, mock_mcp_client):
        """Test list_tools after connection."""
        from Tools.adapters.mcp_bridge import MCPBridge

        bridge = MCPBridge(mock_server_config)
        bridge._connected = True
        bridge._tools_cache = mock_mcp_client.list_tools.return_value

        tools = bridge.list_tools()

        assert len(tools) == 1
        assert tools[0]["name"] == "test_tool"
        assert "inputSchema" in tools[0]

    async def test_call_tool_success(self, mock_server_config, mock_mcp_client):
        """Test successful tool call."""
        from Tools.adapters.mcp_bridge import MCPBridge

        bridge = MCPBridge(mock_server_config)
        bridge._connected = True
        bridge._client = mock_mcp_client

        result = await bridge.call_tool("test_tool", {"param1": "test"})

        assert result.success
        assert result.data == "Test result"
        mock_mcp_client.call_tool.assert_called_once_with(
            "test_tool",
            {"param1": "test"}
        )

    async def test_call_tool_not_connected(self, mock_server_config):
        """Test call_tool when not connected."""
        from Tools.adapters.mcp_bridge import MCPBridge

        bridge = MCPBridge(mock_server_config)

        result = await bridge.call_tool("test_tool", {})

        assert not result.success
        assert "not connected" in result.error.lower()

    async def test_call_tool_error(self, mock_server_config, mock_mcp_client):
        """Test tool call with error."""
        from Tools.adapters.mcp_bridge import MCPBridge

        mock_mcp_client.call_tool = AsyncMock(side_effect=Exception("Test error"))

        bridge = MCPBridge(mock_server_config)
        bridge._connected = True
        bridge._client = mock_mcp_client

        result = await bridge.call_tool("test_tool", {})

        assert not result.success
        assert "Test error" in result.error

    async def test_health_check_healthy(self, mock_server_config):
        """Test health check when connected."""
        from Tools.adapters.mcp_bridge import MCPBridge

        bridge = MCPBridge(mock_server_config)
        bridge._connected = True

        result = await bridge.health_check()

        assert result.success
        assert result.data["status"] == "healthy"

    async def test_health_check_unhealthy(self, mock_server_config):
        """Test health check when not connected."""
        from Tools.adapters.mcp_bridge import MCPBridge

        bridge = MCPBridge(mock_server_config)

        result = await bridge.health_check()

        assert not result.success
        assert "not connected" in result.error.lower()

    async def test_close(self, mock_server_config, mock_mcp_client):
        """Test closing connection."""
        from Tools.adapters.mcp_bridge import MCPBridge

        bridge = MCPBridge(mock_server_config)
        bridge._connected = True
        bridge._client = mock_mcp_client
        bridge._client.exit = AsyncMock()

        await bridge.close()

        assert not bridge._connected
        bridge._client.exit.assert_called_once()

    async def test_close_not_connected(self, mock_server_config):
        """Test close when not connected."""
        from Tools.adapters.mcp_bridge import MCPBridge

        bridge = MCPBridge(mock_server_config)

        # Should not raise exception
        await bridge.close()

        assert not bridge._connected
