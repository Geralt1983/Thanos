"""
Pytest configuration and shared fixtures for Thanos tests.
"""

from pathlib import Path
import sys

import pytest


# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def project_root_path():
    """Return the project root directory path."""
    return project_root


@pytest.fixture
def mock_anthropic_response():
    """Mock a standard Anthropic API response."""
    return {
        "id": "msg_test123",
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": "Test response"}],
        "model": "claude-sonnet-4-5-20250929",
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 100, "output_tokens": 50},
    }


@pytest.fixture
def mock_anthropic_client(mocker, mock_anthropic_response):
    """Mock the Anthropic client for testing."""
    mock_client = mocker.Mock()
    mock_message = mocker.Mock()
    mock_message.content = [mocker.Mock(text="Test response")]
    mock_message.usage = mocker.Mock(input_tokens=100, output_tokens=50)
    mock_message.stop_reason = "end_turn"
    mock_client.messages.create.return_value = mock_message
    return mock_client


@pytest.fixture
def sample_messages():
    """Sample conversation messages for testing."""
    return [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "How are you?"},
        {"role": "assistant", "content": "I'm doing well, thank you!"},
    ]


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary configuration directory."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def mock_api_config(temp_config_dir):
    """Create a mock API configuration file."""
    import json

    config = {
        "anthropic_api_key": "test_api_key_12345",
        "model": "claude-sonnet-4-5-20250929",
    }
    config_file = temp_config_dir / "api.json"
    config_file.write_text(json.dumps(config, indent=2))
    return config_file


# MCP-specific fixtures

@pytest.fixture
def mock_server_config():
    """Create mock MCP server configuration."""
    try:
        from Tools.adapters.mcp_config import MCPServerConfig
        return MCPServerConfig(
            name="test-server",
            command="python",
            args=["-m", "test_server"],
            env={"TEST_VAR": "test_value"},
            transport="stdio",
            description="Test MCP server"
        )
    except ImportError:
        pytest.skip("MCP dependencies not available")


@pytest.fixture
def mock_mcp_client(mocker):
    """Create mock MCP client."""
    mock_client = mocker.AsyncMock()
    mock_client.list_tools = mocker.AsyncMock(return_value=[
        {
            "name": "test_tool",
            "description": "Test tool for unit testing",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "param1": {"type": "string"},
                    "param2": {"type": "integer"}
                },
                "required": ["param1"]
            }
        }
    ])

    mock_client.call_tool = mocker.AsyncMock(return_value={
        "content": [{"type": "text", "text": "Test result"}]
    })

    return mock_client


@pytest.fixture
def mock_mcp_discovery(tmp_path):
    """Create mock MCP server configuration file."""
    import json

    config_file = tmp_path / "mcp_servers.json"
    config_data = {
        "mcpServers": {
            "test-server-1": {
                "command": "python",
                "args": ["-m", "server1"],
                "env": {},
                "transport": "stdio",
                "description": "Test server 1"
            },
            "test-server-2": {
                "command": "node",
                "args": ["server2.js"],
                "env": {"NODE_ENV": "test"},
                "transport": "stdio",
                "description": "Test server 2"
            }
        }
    }

    config_file.write_text(json.dumps(config_data, indent=2))
    return str(config_file)
