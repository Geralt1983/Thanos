"""
Unit tests for MCP error handling and edge cases.
"""

import pytest
from unittest.mock import AsyncMock, patch
from Tools.adapters.base import ToolResult


@pytest.mark.asyncio
class TestMCPErrorHandling:
    """Test MCP error handling and circuit breaker functionality."""

    async def test_connection_timeout(self, mock_server_config):
        """Test connection timeout handling."""
        from Tools.adapters.mcp_bridge import MCPBridge

        with patch("Tools.adapters.mcp_bridge.stdio_client") as mock_client:
            mock_client.side_effect = TimeoutError("Connection timeout")

            bridge = MCPBridge(mock_server_config)

            with pytest.raises(TimeoutError):
                await bridge.connect()

    async def test_tool_call_with_invalid_arguments(self, mock_server_config, mock_mcp_client):
        """Test tool call with invalid arguments."""
        from Tools.adapters.mcp_bridge import MCPBridge

        mock_mcp_client.call_tool = AsyncMock(
            side_effect=ValueError("Invalid arguments")
        )

        bridge = MCPBridge(mock_server_config)
        bridge._connected = True
        bridge._client = mock_mcp_client

        result = await bridge.call_tool("test_tool", {"invalid": "params"})

        assert not result.success
        assert "Invalid arguments" in result.error

    async def test_tool_not_found(self, mock_server_config, mock_mcp_client):
        """Test calling non-existent tool."""
        from Tools.adapters.mcp_bridge import MCPBridge

        mock_mcp_client.call_tool = AsyncMock(
            side_effect=ValueError("Tool not found: nonexistent_tool")
        )

        bridge = MCPBridge(mock_server_config)
        bridge._connected = True
        bridge._client = mock_mcp_client

        result = await bridge.call_tool("nonexistent_tool", {})

        assert not result.success
        assert "Tool not found" in result.error

    async def test_server_crash_during_call(self, mock_server_config, mock_mcp_client):
        """Test handling server crash during tool call."""
        from Tools.adapters.mcp_bridge import MCPBridge

        mock_mcp_client.call_tool = AsyncMock(
            side_effect=ConnectionError("Server disconnected")
        )

        bridge = MCPBridge(mock_server_config)
        bridge._connected = True
        bridge._client = mock_mcp_client

        result = await bridge.call_tool("test_tool", {})

        assert not result.success
        assert "disconnected" in result.error.lower()

    async def test_malformed_server_response(self, mock_server_config, mock_mcp_client):
        """Test handling malformed server response."""
        from Tools.adapters.mcp_bridge import MCPBridge

        mock_mcp_client.call_tool = AsyncMock(
            return_value={"invalid": "response"}  # Missing 'content' field
        )

        bridge = MCPBridge(mock_server_config)
        bridge._connected = True
        bridge._client = mock_mcp_client

        result = await bridge.call_tool("test_tool", {})

        # Should handle gracefully
        assert isinstance(result, ToolResult)

    async def test_empty_tool_result(self, mock_server_config, mock_mcp_client):
        """Test handling empty tool result."""
        from Tools.adapters.mcp_bridge import MCPBridge

        mock_mcp_client.call_tool = AsyncMock(
            return_value={"content": []}
        )

        bridge = MCPBridge(mock_server_config)
        bridge._connected = True
        bridge._client = mock_mcp_client

        result = await bridge.call_tool("test_tool", {})

        assert result.success
        assert result.data in [None, "", []]

    async def test_connection_already_established(self, mock_server_config, mock_mcp_client):
        """Test connecting when already connected."""
        from Tools.adapters.mcp_bridge import MCPBridge

        bridge = MCPBridge(mock_server_config)
        bridge._connected = True
        bridge._client = mock_mcp_client

        # Should not error when already connected
        await bridge.connect()

        assert bridge._connected

    async def test_close_with_error(self, mock_server_config, mock_mcp_client):
        """Test close with error during cleanup."""
        from Tools.adapters.mcp_bridge import MCPBridge

        mock_mcp_client.exit = AsyncMock(side_effect=Exception("Cleanup error"))

        bridge = MCPBridge(mock_server_config)
        bridge._connected = True
        bridge._client = mock_mcp_client

        # Should handle error gracefully
        await bridge.close()

        # Should still mark as disconnected
        assert not bridge._connected
