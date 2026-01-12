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
"""
Pytest configuration and shared fixtures for MCP testing.

Provides mock objects, test data, and common utilities for testing
MCP bridge, discovery, and error handling components.
"""

import asyncio
import json
import tempfile
from pathlib import Path
from typing import Any, AsyncIterator, Iterator
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest


# ============================================================================
# Event Loop Configuration
# ============================================================================


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Mock MCP SDK Components
# ============================================================================


@pytest.fixture
def mock_client_session():
    """Mock MCP ClientSession for testing."""
    session = AsyncMock()

    # Mock initialize result
    init_result = Mock()
    init_result.protocolVersion = "2024-11-05"
    init_result.serverInfo = Mock(name="test-server", version="1.0.0")
    init_result.capabilities = Mock(
        tools=Mock(listChanged=True),
        prompts=None,
        resources=None,
        logging=None,
    )
    session.initialize = AsyncMock(return_value=init_result)

    # Mock list_tools result
    tool1 = Mock()
    tool1.name = "test_tool"
    tool1.description = "A test tool"
    tool1.inputSchema = {
        "type": "object",
        "properties": {
            "arg1": {"type": "string"},
            "arg2": {"type": "integer"},
        },
        "required": ["arg1"],
    }

    tools_result = Mock()
    tools_result.tools = [tool1]
    session.list_tools = AsyncMock(return_value=tools_result)

    # Mock call_tool result
    content_item = Mock()
    content_item.text = '{"result": "success"}'

    tool_result = Mock()
    tool_result.content = [content_item]
    tool_result.isError = False
    session.call_tool = AsyncMock(return_value=tool_result)

    return session


@pytest.fixture
def mock_transport():
    """Mock Transport for testing."""
    from unittest.mock import AsyncMock

    transport = AsyncMock()
    transport.transport_type = "stdio"

    # Mock context manager
    read_stream = AsyncMock()
    write_stream = AsyncMock()

    async def mock_connect():
        yield (read_stream, write_stream)

    transport.connect = mock_connect

    return transport


# ============================================================================
# Test Configuration Files and Directories
# ============================================================================


@pytest.fixture
def temp_dir() -> Iterator[Path]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_mcp_json(temp_dir: Path) -> Path:
    """Create a sample .mcp.json configuration file."""
    config = {
        "mcpServers": {
            "test-server": {
                "transport": {
                    "type": "stdio",
                    "command": "node",
                    "args": ["test.js"],
                    "env": {
                        "API_KEY": "${TEST_API_KEY}"
                    }
                },
                "enabled": True,
                "tags": ["test", "development"]
            },
            "disabled-server": {
                "transport": {
                    "type": "stdio",
                    "command": "node",
                    "args": ["disabled.js"]
                },
                "enabled": False,
                "tags": ["test"]
            }
        }
    }

    config_file = temp_dir / ".mcp.json"
    config_file.write_text(json.dumps(config, indent=2))
    return config_file


@pytest.fixture
def sample_claude_json(temp_dir: Path) -> Path:
    """Create a sample ~/.claude.json configuration file."""
    config = {
        "mcpServers": {
            "workos-mcp": {
                "command": "node",
                "args": ["/path/to/workos/dist/index.js"],
                "env": {
                    "DATABASE_URL": "${DATABASE_URL}"
                }
            },
            "context7": {
                "url": "https://context7.com/mcp",
                "headers": {
                    "Authorization": "Bearer ${CONTEXT7_API_KEY}"
                }
            }
        }
    }

    config_file = temp_dir / ".claude.json"
    config_file.write_text(json.dumps(config, indent=2))
    return config_file


@pytest.fixture
def nested_project_structure(temp_dir: Path) -> dict[str, Path]:
    """
    Create a nested directory structure for testing config discovery.

    Structure:
        temp_dir/
            .mcp.json (root config)
            project/
                .mcp.json (project config)
                subdir/
                    .mcp.json (subdir config)
                    current/  (starting point)
    """
    # Create directories
    project_dir = temp_dir / "project"
    subdir = project_dir / "subdir"
    current = subdir / "current"
    current.mkdir(parents=True)

    # Root config
    root_config = {
        "mcpServers": {
            "root-server": {
                "transport": {
                    "type": "stdio",
                    "command": "node",
                    "args": ["root.js"]
                },
                "tags": ["root"]
            }
        }
    }
    (temp_dir / ".mcp.json").write_text(json.dumps(root_config, indent=2))

    # Project config (overrides root)
    project_config = {
        "mcpServers": {
            "root-server": {
                "transport": {
                    "type": "stdio",
                    "command": "node",
                    "args": ["project.js"]  # Override
                },
                "tags": ["project"]  # Override
            },
            "project-server": {
                "transport": {
                    "type": "stdio",
                    "command": "node",
                    "args": ["project-only.js"]
                },
                "tags": ["project"]
            }
        }
    }
    (project_dir / ".mcp.json").write_text(json.dumps(project_config, indent=2))

    # Subdir config (overrides both)
    subdir_config = {
        "mcpServers": {
            "subdir-server": {
                "transport": {
                    "type": "stdio",
                    "command": "node",
                    "args": ["subdir.js"]
                },
                "tags": ["subdir"]
            }
        }
    }
    (subdir / ".mcp.json").write_text(json.dumps(subdir_config, indent=2))

    return {
        "root": temp_dir,
        "project": project_dir,
        "subdir": subdir,
        "current": current,
    }


# ============================================================================
# Sample MCP Server Configurations
# ============================================================================


@pytest.fixture
def sample_stdio_config():
    """Sample stdio transport configuration."""
    return {
        "type": "stdio",
        "command": "node",
        "args": ["dist/index.js"],
        "env": {
            "DATABASE_URL": "postgresql://localhost/test",
            "NODE_ENV": "test",
        }
    }


@pytest.fixture
def sample_sse_config():
    """Sample SSE transport configuration."""
    return {
        "type": "sse",
        "url": "https://example.com/mcp",
        "headers": {
            "Authorization": "Bearer test-token"
        },
        "timeout": 30
    }


@pytest.fixture
def sample_server_config(sample_stdio_config):
    """Sample complete server configuration."""
    return {
        "name": "test-server",
        "transport": sample_stdio_config,
        "enabled": True,
        "tags": ["test", "development"],
    }


# ============================================================================
# Mock Tool Results and Test Data
# ============================================================================


@pytest.fixture
def sample_tools():
    """Sample tool definitions in Thanos format."""
    return [
        {
            "name": "get_tasks",
            "description": "Get tasks from database",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["active", "completed", "archived"]
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100
                    }
                },
                "required": ["status"]
            }
        },
        {
            "name": "create_task",
            "description": "Create a new task",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high"]
                    }
                },
                "required": ["title"]
            }
        }
    ]


@pytest.fixture
def sample_tool_arguments():
    """Sample arguments for testing tool calls."""
    return {
        "valid_args": {
            "status": "active",
            "limit": 10
        },
        "invalid_args": {
            "status": "invalid_status",  # Not in enum
            "limit": 200  # Exceeds maximum
        },
        "missing_required": {
            "limit": 10  # Missing required 'status'
        }
    }


# ============================================================================
# Error Testing Fixtures
# ============================================================================


@pytest.fixture
def error_scenarios():
    """Common error scenarios for testing."""
    return {
        "connection_error": {
            "message": "Failed to connect to server",
            "server_name": "test-server",
            "retryable": True
        },
        "timeout_error": {
            "message": "Operation timed out",
            "timeout_seconds": 30.0,
            "server_name": "test-server",
            "retryable": True
        },
        "protocol_error": {
            "message": "Invalid protocol response",
            "server_name": "test-server",
            "retryable": False
        },
        "tool_not_found": {
            "message": "Tool not found",
            "tool_name": "nonexistent_tool",
            "available_tools": ["get_tasks", "create_task"],
            "server_name": "test-server",
            "retryable": False
        },
        "validation_error": {
            "message": "Validation error",
            "tool_name": "get_tasks",
            "validation_error": "Missing required field: status",
            "provided_arguments": {"limit": 10},
            "server_name": "test-server",
            "retryable": False
        }
    }


# ============================================================================
# Helper Functions
# ============================================================================


def create_mock_mcp_server(name: str, tools: list[dict] = None) -> Mock:
    """
    Create a mock MCP server for testing.

    Args:
        name: Server name
        tools: List of tool definitions

    Returns:
        Mock server instance
    """
    if tools is None:
        tools = []

    server = Mock()
    server.name = name
    server.list_tools = Mock(return_value=tools)
    server.call_tool = AsyncMock()

    return server


# ============================================================================
# Async Testing Utilities
# ============================================================================


@pytest.fixture
def run_async():
    """Helper to run async functions in tests."""
    def _run(coro):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)
    return _run
