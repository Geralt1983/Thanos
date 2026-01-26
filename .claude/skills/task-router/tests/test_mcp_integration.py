#!/usr/bin/env python3
"""
Integration tests for task-router skill MCP integration.

Tests the task-router skill's ability to interact with MCP servers,
including WorkOS and Oura integrations, energy-aware gating, and
task operation execution.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, MagicMock, patch
from datetime import datetime
from pathlib import Path
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from Tools.adapters.base import ToolResult
from Tools.adapters.mcp_bridge import MCPBridge
from Tools.adapters.mcp_config import MCPServerConfig, StdioConfig


# Import workflow after path setup
@pytest.fixture(autouse=True)
def setup_workflow_imports():
    """Ensure workflow module is importable."""
    workflow_path = Path(__file__).parent.parent / "workflow.py"
    assert workflow_path.exists(), f"workflow.py not found at {workflow_path}"

    # Import workflow functions
    import importlib.util
    spec = importlib.util.spec_from_file_location("task_router_workflow", workflow_path)
    workflow = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(workflow)

    return workflow


@pytest.fixture
def mock_workos_client():
    """Create a mock WorkOS MCP client."""
    client = Mock(spec=MCPBridge)
    client.name = "workos"
    client.call_tool = AsyncMock()
    return client


@pytest.fixture
def mock_oura_client():
    """Create a mock Oura MCP client."""
    client = Mock(spec=MCPBridge)
    client.name = "oura"
    client.call_tool = AsyncMock()
    return client


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


class TestMCPClientInitialization:
    """Test MCP client initialization for task-router skill."""

    def test_workos_client_initialization(self, setup_workflow_imports):
        """Test WorkOS MCP client initialization."""
        workflow = setup_workflow_imports

        with patch.object(Path, 'exists', return_value=True):
            with patch('task_router_workflow.MCPBridge') as MockBridge:
                mock_client = Mock(spec=MCPBridge)
                MockBridge.return_value = mock_client

                # Clear cache
                workflow._mcp_client_cache = None

                client = workflow._get_mcp_client()

                # Should initialize successfully
                assert client is not None
                assert MockBridge.called

    def test_oura_client_initialization(self, setup_workflow_imports):
        """Test Oura MCP client initialization."""
        workflow = setup_workflow_imports

        with patch.object(Path, 'exists', return_value=True):
            with patch('task_router_workflow.MCPBridge') as MockBridge:
                mock_client = Mock(spec=MCPBridge)
                MockBridge.return_value = mock_client

                # Clear cache
                workflow._oura_client_cache = None

                client = workflow._get_oura_client()

                # Should initialize successfully
                assert client is not None
                assert MockBridge.called

    def test_client_caching(self, setup_workflow_imports):
        """Test that MCP clients are cached after first initialization."""
        workflow = setup_workflow_imports

        with patch.object(Path, 'exists', return_value=True):
            with patch('task_router_workflow.MCPBridge') as MockBridge:
                mock_client = Mock(spec=MCPBridge)
                MockBridge.return_value = mock_client

                # Clear cache
                workflow._mcp_client_cache = None

                # First call
                client1 = workflow._get_mcp_client()
                call_count_first = MockBridge.call_count

                # Second call (should use cache)
                client2 = workflow._get_mcp_client()
                call_count_second = MockBridge.call_count

                # Should return same client without creating new one
                assert client1 is client2
                assert call_count_second == call_count_first

    def test_missing_server_graceful_degradation(self, setup_workflow_imports):
        """Test graceful degradation when MCP server is missing."""
        workflow = setup_workflow_imports

        with patch.object(Path, 'exists', return_value=False):
            # Clear cache
            workflow._mcp_client_cache = None

            client = workflow._get_mcp_client()

            # Should return None but not crash
            assert client is None

    def test_missing_bun_command_graceful_degradation(self, setup_workflow_imports):
        """Test graceful degradation when bun command is not found."""
        workflow = setup_workflow_imports

        with patch.object(Path, 'exists', return_value=True):
            with patch('task_router_workflow.MCPBridge', side_effect=FileNotFoundError("bun not found")):
                # Clear cache
                workflow._mcp_client_cache = None

                client = workflow._get_mcp_client()

                # Should return None but not crash
                assert client is None


class TestEnergyLevelRetrieval:
    """Test energy level retrieval from MCP servers."""

    @pytest.mark.asyncio
    async def test_oura_readiness_fetch(self, setup_workflow_imports, mock_oura_client, sample_energy_data):
        """Test fetching readiness score from Oura MCP."""
        workflow = setup_workflow_imports

        # Mock Oura response
        mock_oura_client.call_tool.return_value = ToolResult.ok(
            sample_energy_data["oura_readiness"]
        )

        with patch('task_router_workflow._get_oura_client', return_value=mock_oura_client):
            score, level = await workflow._get_energy_level_async()

            # Should get Oura readiness
            assert score == 75
            assert level == "medium"
            mock_oura_client.call_tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_workos_energy_fallback(self, setup_workflow_imports, mock_workos_client, sample_energy_data):
        """Test falling back to WorkOS energy when Oura unavailable."""
        workflow = setup_workflow_imports

        # Mock WorkOS response
        mock_workos_client.call_tool.return_value = ToolResult.ok(
            sample_energy_data["workos_energy"]
        )

        with patch('task_router_workflow._get_oura_client', return_value=None):
            with patch('task_router_workflow._get_mcp_client', return_value=mock_workos_client):
                score, level = await workflow._get_energy_level_async()

                # Should fall back to WorkOS
                assert score == 75  # Mapped from "medium"
                assert level == "medium"
                mock_workos_client.call_tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_energy_level_timeout_handling(self, setup_workflow_imports, mock_oura_client):
        """Test handling of MCP call timeouts."""
        workflow = setup_workflow_imports

        # Mock timeout
        mock_oura_client.call_tool.side_effect = asyncio.TimeoutError()

        with patch('task_router_workflow._get_oura_client', return_value=mock_oura_client):
            with patch('task_router_workflow._get_mcp_client', return_value=None):
                score, level = await workflow._get_energy_level_async()

                # Should fall back to default
                assert score == 75
                assert level == "medium"

    @pytest.mark.asyncio
    async def test_energy_level_connection_error(self, setup_workflow_imports, mock_oura_client):
        """Test handling of connection errors."""
        workflow = setup_workflow_imports

        # Mock connection error
        mock_oura_client.call_tool.side_effect = ConnectionRefusedError()

        with patch('task_router_workflow._get_oura_client', return_value=mock_oura_client):
            with patch('task_router_workflow._get_mcp_client', return_value=None):
                score, level = await workflow._get_energy_level_async()

                # Should fall back to default
                assert score == 75
                assert level == "medium"

    def test_energy_mapping(self, setup_workflow_imports):
        """Test energy score to level mapping."""
        workflow = setup_workflow_imports

        # Test different score ranges
        assert workflow.map_readiness_to_energy(90) == "high"
        assert workflow.map_readiness_to_energy(85) == "high"
        assert workflow.map_readiness_to_energy(75) == "medium"
        assert workflow.map_readiness_to_energy(70) == "medium"
        assert workflow.map_readiness_to_energy(65) == "low"
        assert workflow.map_readiness_to_energy(50) == "low"


class TestTaskOperationExecution:
    """Test task operation execution via MCP."""

    @pytest.mark.asyncio
    async def test_create_task_operation(self, setup_workflow_imports, mock_workos_client, sample_task_data):
        """Test creating a task via MCP."""
        workflow = setup_workflow_imports

        # Mock successful task creation
        mock_workos_client.call_tool.return_value = ToolResult.ok(sample_task_data)

        intent = workflow.TaskIntent(
            action="create",
            title="Review Q4 planning document",
            value_tier="checkbox",
            cognitive_load="medium"
        )

        result = await workflow._execute_task_operation_async(intent, mock_workos_client)

        # Should succeed
        assert result["success"] is True
        assert result["task"]["id"] == 123
        assert result["points"] > 0
        mock_workos_client.call_tool.assert_called_with(
            "workos_create_task",
            {
                "title": "Review Q4 planning document",
                "valueTier": "checkbox",
                "drainType": "shallow",
                "status": "active"
            }
        )

    @pytest.mark.asyncio
    async def test_complete_task_operation(self, setup_workflow_imports, mock_workos_client):
        """Test completing a task via MCP."""
        workflow = setup_workflow_imports

        # Mock successful task completion
        mock_workos_client.call_tool.side_effect = [
            ToolResult.ok({"id": 123, "status": "completed"}),
            ToolResult.ok({"pointsToday": 5, "dailyGoal": 18})
        ]

        intent = workflow.TaskIntent(
            action="complete",
            task_id=123,
            title="Passport task",
            value_tier="checkbox"
        )

        result = await workflow._execute_task_operation_async(intent, mock_workos_client)

        # Should succeed with progress
        assert result["success"] is True
        assert result["progress"] == 5
        assert result["target"] == 18

    @pytest.mark.asyncio
    async def test_query_tasks_operation(self, setup_workflow_imports, mock_workos_client, sample_task_data):
        """Test querying tasks via MCP."""
        workflow = setup_workflow_imports

        # Mock task list
        mock_workos_client.call_tool.return_value = ToolResult.ok([
            sample_task_data,
            {**sample_task_data, "id": 124, "title": "Another task"}
        ])

        intent = workflow.TaskIntent(
            action="query",
            status="active"
        )

        result = await workflow._execute_task_operation_async(intent, mock_workos_client)

        # Should return tasks
        assert result["success"] is True
        assert len(result["tasks"]) == 2
        assert result["tasks"][0]["id"] == 123

    @pytest.mark.asyncio
    async def test_task_operation_timeout(self, setup_workflow_imports, mock_workos_client):
        """Test handling of task operation timeouts."""
        workflow = setup_workflow_imports

        # Mock timeout
        mock_workos_client.call_tool.side_effect = asyncio.TimeoutError()

        intent = workflow.TaskIntent(
            action="create",
            title="Test task"
        )

        result = await workflow._execute_task_operation_async(intent, mock_workos_client)

        # Should fail gracefully
        assert result["success"] is False
        assert "timed out" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_task_operation_connection_error(self, setup_workflow_imports, mock_workos_client):
        """Test handling of connection errors during task operations."""
        workflow = setup_workflow_imports

        # Mock connection error
        mock_workos_client.call_tool.side_effect = ConnectionRefusedError()

        intent = workflow.TaskIntent(
            action="create",
            title="Test task"
        )

        result = await workflow._execute_task_operation_async(intent, mock_workos_client)

        # Should fail gracefully
        assert result["success"] is False
        assert "cannot connect" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_promote_task_operation(self, setup_workflow_imports, mock_workos_client):
        """Test promoting a task via MCP."""
        workflow = setup_workflow_imports

        # Mock successful promotion
        mock_workos_client.call_tool.return_value = ToolResult.ok({"id": 123, "status": "active"})

        intent = workflow.TaskIntent(
            action="promote",
            task_id=123,
            title="Test task"
        )

        result = await workflow._execute_task_operation_async(intent, mock_workos_client)

        # Should succeed
        assert result["success"] is True


class TestEnergyAwareGating:
    """Test energy-aware task gating functionality."""

    def test_gate_high_complexity_on_low_energy(self, setup_workflow_imports):
        """Test that high-complexity tasks are gated when energy is low."""
        workflow = setup_workflow_imports

        intent = workflow.TaskIntent(
            action="create",
            title="Design new architecture",
            cognitive_load="high"
        )

        should_gate = workflow.should_gate_task(intent, "low")

        assert should_gate is True

    def test_allow_low_complexity_on_low_energy(self, setup_workflow_imports):
        """Test that low-complexity tasks are allowed when energy is low."""
        workflow = setup_workflow_imports

        intent = workflow.TaskIntent(
            action="create",
            title="Review document",
            cognitive_load="low"
        )

        should_gate = workflow.should_gate_task(intent, "low")

        assert should_gate is False

    def test_allow_high_complexity_on_high_energy(self, setup_workflow_imports):
        """Test that high-complexity tasks are allowed when energy is high."""
        workflow = setup_workflow_imports

        intent = workflow.TaskIntent(
            action="create",
            title="Design new architecture",
            cognitive_load="high"
        )

        should_gate = workflow.should_gate_task(intent, "high")

        assert should_gate is False

    def test_suggested_alternatives_for_low_energy(self, setup_workflow_imports):
        """Test suggested alternatives when energy is low."""
        workflow = setup_workflow_imports

        alternatives = workflow.get_suggested_alternatives("low")

        assert len(alternatives) > 0
        assert any("brain dump" in alt.lower() for alt in alternatives)
        assert any("review" in alt.lower() for alt in alternatives)


class TestEndToEndWorkflow:
    """Test end-to-end workflow execution."""

    def test_complete_task_creation_workflow(self, setup_workflow_imports, mock_workos_client, sample_task_data):
        """Test complete workflow for creating a task."""
        workflow = setup_workflow_imports

        # Mock energy check and task creation
        mock_workos_client.call_tool.side_effect = [
            ToolResult.ok([{"level": "high"}]),  # Energy check
            ToolResult.ok(sample_task_data)  # Task creation
        ]

        with patch('task_router_workflow._get_oura_client', return_value=None):
            with patch('task_router_workflow._get_mcp_client', return_value=mock_workos_client):
                result = workflow.execute_task_operation(
                    "Add a task to review the Q4 planning document",
                    mcp_client=mock_workos_client
                )

        # Should succeed
        assert result["success"] is True
        assert result["action"] == "create"
        assert "sacrifices" in result["response"].lower()

    def test_gated_task_workflow(self, setup_workflow_imports, mock_workos_client):
        """Test workflow when task is gated due to low energy."""
        workflow = setup_workflow_imports

        # Mock low energy
        mock_workos_client.call_tool.return_value = ToolResult.ok([{"level": "low"}])

        with patch('task_router_workflow._get_oura_client', return_value=None):
            with patch('task_router_workflow._get_mcp_client', return_value=mock_workos_client):
                result = workflow.execute_task_operation(
                    "Add a task to design the entire system architecture",
                    mcp_client=mock_workos_client
                )

        # Should be gated
        assert result["success"] is False
        assert "low power state" in result["response"].lower()
        assert "stones require charging" in result["response"].lower()

    def test_query_tasks_workflow(self, setup_workflow_imports, mock_workos_client, sample_task_data):
        """Test workflow for querying tasks."""
        workflow = setup_workflow_imports

        # Mock energy check and task query
        mock_workos_client.call_tool.side_effect = [
            ToolResult.ok([{"level": "medium"}]),  # Energy check
            ToolResult.ok([sample_task_data])  # Task list
        ]

        with patch('task_router_workflow._get_oura_client', return_value=None):
            with patch('task_router_workflow._get_mcp_client', return_value=mock_workos_client):
                result = workflow.execute_task_operation(
                    "Show me my active tasks",
                    mcp_client=mock_workos_client
                )

        # Should succeed
        assert result["success"] is True
        assert result["action"] == "query"
        assert "sacrifices" in result["response"].lower()

    def test_workflow_with_unavailable_mcp(self, setup_workflow_imports):
        """Test workflow gracefully handles unavailable MCP server."""
        workflow = setup_workflow_imports

        with patch('task_router_workflow._get_oura_client', return_value=None):
            with patch('task_router_workflow._get_mcp_client', return_value=None):
                result = workflow.execute_task_operation(
                    "Add a task to review document"
                )

        # Should fail gracefully with helpful message
        assert result["success"] is False
        assert "unavailable" in result["response"].lower()


class TestIntentParsing:
    """Test intent parsing from user messages."""

    def test_parse_create_intent(self, setup_workflow_imports):
        """Test parsing create task intent."""
        workflow = setup_workflow_imports

        intent = workflow.parse_intent("Add a task to review the Q4 planning document")

        assert intent.action == "create"
        assert "review" in intent.title.lower()

    def test_parse_complete_intent(self, setup_workflow_imports):
        """Test parsing complete task intent."""
        workflow = setup_workflow_imports

        intent = workflow.parse_intent("Complete the passport application task")

        assert intent.action == "complete"

    def test_parse_query_intent(self, setup_workflow_imports):
        """Test parsing query tasks intent."""
        workflow = setup_workflow_imports

        intent = workflow.parse_intent("Show me my active tasks")

        assert intent.action == "query"

    def test_complexity_detection(self, setup_workflow_imports):
        """Test cognitive load detection from keywords."""
        workflow = setup_workflow_imports

        # High complexity
        intent_high = workflow.parse_intent("Add a task to design the system architecture")
        assert intent_high.cognitive_load == "high"

        # Low complexity
        intent_low = workflow.parse_intent("Add a task to review the document")
        assert intent_low.cognitive_load == "low"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
