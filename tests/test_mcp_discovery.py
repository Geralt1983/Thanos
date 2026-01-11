"""
Unit tests for MCP server discovery.
"""

import json
import pytest
from pathlib import Path


@pytest.mark.asyncio
class TestMCPDiscovery:
    """Test MCP server discovery functionality."""

    async def test_discover_servers_from_file(self, mock_mcp_discovery):
        """Test discovering servers from configuration file."""
        from Tools.adapters.mcp_discovery import discover_servers

        servers = await discover_servers(config_path=mock_mcp_discovery)

        assert len(servers) == 2
        assert any(s.name == "test-server-1" for s in servers)
        assert any(s.name == "test-server-2" for s in servers)

    async def test_discover_servers_file_not_found(self, tmp_path):
        """Test discovery with missing config file."""
        from Tools.adapters.mcp_discovery import discover_servers

        nonexistent = str(tmp_path / "nonexistent.json")

        servers = await discover_servers(config_path=nonexistent)

        assert servers == []

    async def test_discover_servers_invalid_json(self, tmp_path):
        """Test discovery with invalid JSON."""
        from Tools.adapters.mcp_discovery import discover_servers

        config_file = tmp_path / "invalid.json"
        config_file.write_text("{ invalid json }")

        servers = await discover_servers(config_path=str(config_file))

        assert servers == []

    async def test_discover_servers_empty_config(self, tmp_path):
        """Test discovery with empty configuration."""
        from Tools.adapters.mcp_discovery import discover_servers

        config_file = tmp_path / "empty.json"
        config_file.write_text(json.dumps({"mcpServers": {}}))

        servers = await discover_servers(config_path=str(config_file))

        assert servers == []

    async def test_get_server_config_by_name(self, mock_mcp_discovery):
        """Test getting specific server configuration."""
        from Tools.adapters.mcp_discovery import get_server_config

        config = await get_server_config("test-server-1", config_path=mock_mcp_discovery)

        assert config is not None
        assert config.name == "test-server-1"
        assert config.command == "python"

    async def test_get_server_config_not_found(self, mock_mcp_discovery):
        """Test getting non-existent server configuration."""
        from Tools.adapters.mcp_discovery import get_server_config

        config = await get_server_config("nonexistent", config_path=mock_mcp_discovery)

        assert config is None

    async def test_server_config_parsing(self, tmp_path):
        """Test detailed server configuration parsing."""
        from Tools.adapters.mcp_discovery import discover_servers

        config_file = tmp_path / "test_config.json"
        config_data = {
            "mcpServers": {
                "detailed-server": {
                    "command": "npx",
                    "args": ["-y", "@test/server"],
                    "env": {
                        "API_KEY": "test_key",
                        "DEBUG": "true"
                    },
                    "transport": "stdio",
                    "description": "Detailed test server"
                }
            }
        }
        config_file.write_text(json.dumps(config_data))

        servers = await discover_servers(config_path=str(config_file))

        assert len(servers) == 1
        server = servers[0]
        assert server.name == "detailed-server"
        assert server.command == "npx"
        assert server.args == ["-y", "@test/server"]
        assert server.env["API_KEY"] == "test_key"
        assert server.transport == "stdio"
