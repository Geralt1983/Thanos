"""
Pytest configuration and shared fixtures for task-router skill tests.

Provides MCP mocks, test data, and utilities for testing task-router
skill integration with WorkOS and Oura MCP servers.
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest


# ============================================================================
# Path Configuration
# ============================================================================

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Add skill directory to path
SKILL_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SKILL_DIR))


@pytest.fixture
def project_root_path():
    """Return the project root directory path."""
    return PROJECT_ROOT


@pytest.fixture
def skill_dir_path():
    """Return the skill directory path."""
    return SKILL_DIR


# ============================================================================
# Workflow Module Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def setup_workflow_imports():
    """Ensure workflow module is importable for all tests."""
    workflow_path = SKILL_DIR / "workflow.py"
    assert workflow_path.exists(), f"workflow.py not found at {workflow_path}"

    # Import workflow functions
    import importlib.util
    spec = importlib.util.spec_from_file_location("task_router_workflow", workflow_path)
    workflow = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(workflow)

    return workflow


# ============================================================================
# MCP Client Mocks
# ============================================================================


@pytest.fixture
def mock_workos_client():
    """Create a mock WorkOS MCP client."""
    from Tools.adapters.mcp_bridge import MCPBridge
    from Tools.adapters.base import ToolResult

    client = Mock(spec=MCPBridge)
    client.name = "workos"
    client.call_tool = AsyncMock()

    # Default successful response - ToolResult with success and data
    client.call_tool.return_value = ToolResult.ok({"result": "success"})

    return client


@pytest.fixture
def mock_oura_client():
    """Create a mock Oura MCP client."""
    from Tools.adapters.mcp_bridge import MCPBridge
    from Tools.adapters.base import ToolResult

    client = Mock(spec=MCPBridge)
    client.name = "oura"
    client.call_tool = AsyncMock()

    # Default successful response - ToolResult with success and data
    client.call_tool.return_value = ToolResult.ok({"result": "success"})

    return client


@pytest.fixture
def mock_mcp_bridge():
    """Create a generic mock MCP bridge."""
    from Tools.adapters.mcp_bridge import MCPBridge

    bridge = Mock(spec=MCPBridge)
    bridge.call_tool = AsyncMock()
    bridge.list_tools = AsyncMock(return_value=[])

    return bridge


# ============================================================================
# Sample Test Data
# ============================================================================


@pytest.fixture
def sample_task_data():
    """Sample task data for testing."""
    return {
        "id": 123,
        "title": "Review Q4 planning document",
        "valueTier": "checkbox",
        "drainType": "shallow",
        "status": "active",
        "cognitiveLoad": "medium",
        "createdAt": "2024-01-01T12:00:00Z"
    }


@pytest.fixture
def sample_tasks_list():
    """Sample list of tasks for testing."""
    return [
        {
            "id": 1,
            "title": "Quick task",
            "valueTier": "checkbox",
            "drainType": "shallow",
            "status": "active",
            "cognitiveLoad": "low"
        },
        {
            "id": 2,
            "title": "Deep work task",
            "valueTier": "keystone",
            "drainType": "deep",
            "status": "active",
            "cognitiveLoad": "high"
        },
        {
            "id": 3,
            "title": "Medium task",
            "valueTier": "milestone",
            "drainType": "medium",
            "status": "active",
            "cognitiveLoad": "medium"
        }
    ]


@pytest.fixture
def sample_energy_data():
    """Sample energy data for testing."""
    return {
        "workos_energy": [
            {
                "level": "medium",
                "note": "Feeling okay",
                "timestamp": "2024-01-01T09:00:00Z"
            }
        ],
        "oura_readiness": [
            {
                "score": 75,
                "contributors": {
                    "sleep_score": 80,
                    "hrv_balance": 70
                },
                "day": "2024-01-01"
            }
        ]
    }


@pytest.fixture
def low_energy_data():
    """Sample low energy data for testing energy gating."""
    return {
        "workos_energy": [
            {
                "level": "low",
                "note": "Exhausted",
                "timestamp": "2024-01-01T09:00:00Z"
            }
        ],
        "oura_readiness": [
            {
                "score": 45,
                "contributors": {
                    "sleep_score": 40,
                    "hrv_balance": 35
                },
                "day": "2024-01-01"
            }
        ]
    }


@pytest.fixture
def high_energy_data():
    """Sample high energy data for testing."""
    return {
        "workos_energy": [
            {
                "level": "high",
                "note": "Energized",
                "timestamp": "2024-01-01T09:00:00Z"
            }
        ],
        "oura_readiness": [
            {
                "score": 90,
                "contributors": {
                    "sleep_score": 95,
                    "hrv_balance": 88
                },
                "day": "2024-01-01"
            }
        ]
    }


# ============================================================================
# Tool Result Fixtures
# ============================================================================


@pytest.fixture
def sample_tool_result():
    """Sample ToolResult for testing."""
    from Tools.adapters.base import ToolResult

    return ToolResult(
        success=True,
        data={"result": "success"},
        error=None,
        metadata={"tool_name": "test_tool", "server": "test-server"}
    )


@pytest.fixture
def error_tool_result():
    """Sample error ToolResult for testing."""
    from Tools.adapters.base import ToolResult

    return ToolResult(
        success=False,
        data=None,
        error="Operation failed",
        metadata={"tool_name": "test_tool", "server": "test-server"}
    )


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
# Async Testing Utilities
# ============================================================================


@pytest.fixture
def run_async():
    """Helper to run async functions in tests."""
    def _run(coro):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)
    return _run
