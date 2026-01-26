"""
Pytest configuration and shared fixtures for health-insight skill tests.

Provides MCP mocks, test data, and utilities for testing health-insight
skill integration with Oura and WorkOS MCP servers.
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

    # Import workflow module
    import importlib.util
    spec = importlib.util.spec_from_file_location("health_insight_workflow", workflow_path)
    workflow = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(workflow)

    return workflow


# ============================================================================
# MCP Client Mocks
# ============================================================================


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
def mock_mcp_bridge():
    """Create a generic mock MCP bridge."""
    from Tools.adapters.mcp_bridge import MCPBridge

    bridge = Mock(spec=MCPBridge)
    bridge.call_tool = AsyncMock()
    bridge.list_tools = AsyncMock(return_value=[])

    return bridge


# ============================================================================
# Sample Health Data
# ============================================================================


@pytest.fixture
def sample_oura_readiness():
    """Sample Oura readiness data."""
    return {
        "data": [
            {
                "id": "test-readiness-1",
                "day": "2024-01-01",
                "score": 75,
                "temperature_deviation": 0.1,
                "temperature_trend_deviation": 0.2,
                "contributors": {
                    "activity_balance": 70,
                    "body_temperature": 75,
                    "hrv_balance": 80,
                    "previous_day_activity": 85,
                    "previous_night": 90,
                    "recovery_index": 65,
                    "resting_heart_rate": 72,
                    "sleep_balance": 88
                }
            }
        ]
    }


@pytest.fixture
def sample_oura_sleep():
    """Sample Oura sleep data."""
    return {
        "data": [
            {
                "id": "test-sleep-1",
                "day": "2024-01-01",
                "score": 82,
                "total_sleep_duration": 28800,
                "efficiency": 88,
                "restfulness": 75,
                "rem_sleep_duration": 7200,
                "deep_sleep_duration": 5400,
                "light_sleep_duration": 16200,
                "latency": 480,
                "timing": 85,
                "awake_time": 1200
            }
        ]
    }


@pytest.fixture
def sample_oura_activity():
    """Sample Oura activity data."""
    return {
        "data": [
            {
                "id": "test-activity-1",
                "day": "2024-01-01",
                "score": 78,
                "active_calories": 650,
                "steps": 8500,
                "equivalent_walking_distance": 6800,
                "high_activity_time": 3600,
                "medium_activity_time": 7200,
                "low_activity_time": 14400,
                "sedentary_time": 28800,
                "total_calories": 2200
            }
        ]
    }


@pytest.fixture
def low_readiness_data():
    """Sample low readiness data for testing energy gating."""
    return {
        "data": [
            {
                "id": "test-readiness-low",
                "day": "2024-01-01",
                "score": 45,
                "contributors": {
                    "sleep_score": 40,
                    "hrv_balance": 35,
                    "resting_heart_rate": 30
                }
            }
        ]
    }


@pytest.fixture
def high_readiness_data():
    """Sample high readiness data for testing."""
    return {
        "data": [
            {
                "id": "test-readiness-high",
                "day": "2024-01-01",
                "score": 92,
                "contributors": {
                    "sleep_score": 95,
                    "hrv_balance": 90,
                    "resting_heart_rate": 88
                }
            }
        ]
    }


# ============================================================================
# Sample Task Data
# ============================================================================


@pytest.fixture
def sample_tasks():
    """Sample tasks data for testing."""
    return [
        {
            "id": 1,
            "title": "Light task",
            "valueTier": "checkbox",
            "drainType": "shallow",
            "status": "active",
            "cognitiveLoad": "low"
        },
        {
            "id": 2,
            "title": "Medium task",
            "valueTier": "milestone",
            "drainType": "medium",
            "status": "active",
            "cognitiveLoad": "medium"
        },
        {
            "id": 3,
            "title": "Deep work task",
            "valueTier": "keystone",
            "drainType": "deep",
            "status": "active",
            "cognitiveLoad": "high"
        }
    ]


@pytest.fixture
def sample_workos_energy():
    """Sample WorkOS energy data."""
    return [
        {
            "level": "medium",
            "note": "Feeling okay",
            "timestamp": "2024-01-01T09:00:00Z"
        }
    ]


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


# ============================================================================
# Mapping Helper Fixtures
# ============================================================================


@pytest.fixture
def energy_level_mappings():
    """Energy level mapping test data."""
    return {
        "low": {"min": 0, "max": 59},
        "medium": {"min": 60, "max": 79},
        "high": {"min": 80, "max": 100}
    }


@pytest.fixture
def visual_state_mappings():
    """Visual state mapping test data."""
    return {
        "CHAOS": ["morning", "unsorted"],
        "FOCUS": ["deep_work", "engaged"],
        "BALANCE": ["complete", "achieved"]
    }
