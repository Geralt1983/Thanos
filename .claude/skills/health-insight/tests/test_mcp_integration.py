"""
Integration tests for health-insight skill MCP integration.

Tests the MCP client usage in the health-insight workflow including:
- Oura MCP client initialization and health data retrieval
- WorkOS MCP client initialization and task fetching
- Timeout handling and error recovery
- Graceful degradation when MCP servers are unavailable
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from pathlib import Path
import sys

# Add parent directory to path for imports
SKILL_DIR = Path(__file__).parent.parent
PROJECT_ROOT = SKILL_DIR.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SKILL_DIR))

from workflow import (
    _get_oura_client,
    _get_workos_client,
    _get_health_snapshot_async,
    _get_energy_appropriate_tasks_async,
    get_health_snapshot,
    get_energy_appropriate_tasks,
    execute_health_insight,
    map_readiness_to_energy,
    determine_visual_state,
    MCP_CALL_TIMEOUT_SECONDS,
)

from Tools.adapters.mcp_bridge import MCPBridge
from Tools.adapters.base import ToolResult


class TestMCPClientInitialization:
    """Test MCP client initialization for Oura and WorkOS."""

    def test_oura_client_initialization_success(self):
        """Test successful Oura MCP client initialization."""
        # Mock the server file existence
        with patch.object(Path, 'exists', return_value=True):
            with patch('workflow.MCPBridge') as mock_bridge:
                mock_instance = Mock()
                mock_bridge.return_value = mock_instance

                client = _get_oura_client()

                # Should return MCPBridge instance
                assert client is not None
                assert client == mock_instance

    def test_oura_client_missing_server(self):
        """Test Oura client handles missing server gracefully."""
        # Mock the server file not existing
        with patch.object(Path, 'exists', return_value=False):
            client = _get_oura_client()

            # Should return None when server not found
            assert client is None

    def test_oura_client_bun_not_found(self):
        """Test Oura client handles missing bun command."""
        with patch.object(Path, 'exists', return_value=True):
            with patch('workflow.MCPBridge', side_effect=FileNotFoundError("bun not found")):
                client = _get_oura_client()

                # Should return None when bun not found
                assert client is None

    def test_workos_client_initialization_success(self):
        """Test successful WorkOS MCP client initialization."""
        # Mock the server file existence
        with patch.object(Path, 'exists', return_value=True):
            with patch('workflow.MCPBridge') as mock_bridge:
                mock_instance = Mock()
                mock_bridge.return_value = mock_instance

                client = _get_workos_client()

                # Should return MCPBridge instance
                assert client is not None
                assert client == mock_instance

    def test_workos_client_missing_server(self):
        """Test WorkOS client handles missing server gracefully."""
        # Mock the server file not existing
        with patch.object(Path, 'exists', return_value=False):
            client = _get_workos_client()

            # Should return None when server not found
            assert client is None


class TestHealthSnapshotRetrieval:
    """Test health snapshot retrieval with MCP calls."""

    @pytest.mark.asyncio
    async def test_get_health_snapshot_success(self):
        """Test successful health snapshot retrieval."""
        # Mock MCP client
        mock_client = AsyncMock(spec=MCPBridge)

        # Mock readiness response
        readiness_result = ToolResult(
            success=True,
            data=[{"score": 85}],
            error=None
        )

        # Mock sleep response
        sleep_result = ToolResult(
            success=True,
            data=[{"score": 90}],
            error=None
        )

        # Mock activity response
        activity_result = ToolResult(
            success=True,
            data=[{"steps": 10000, "active_calories": 500}],
            error=None
        )

        # Configure mock to return different results for different calls
        mock_client.call_tool = AsyncMock(side_effect=[
            readiness_result,
            sleep_result,
            activity_result
        ])

        today = "2024-01-25"
        snapshot = await _get_health_snapshot_async(mock_client, today)

        # Verify data was retrieved
        assert snapshot["readiness"] == 85
        assert snapshot["sleep_score"] == 90
        assert snapshot["activity"]["steps"] == 10000
        assert snapshot["activity"]["active_calories"] == 500

    @pytest.mark.asyncio
    async def test_get_health_snapshot_with_none_client(self):
        """Test health snapshot with None client falls back to placeholders."""
        today = "2024-01-25"
        snapshot = await _get_health_snapshot_async(None, today)

        # Should return default values
        assert snapshot["readiness"] == 75
        assert snapshot["sleep_score"] == 82
        assert "steps" in snapshot["activity"]
        assert "stress_high" in snapshot["stress"]

    @pytest.mark.asyncio
    async def test_get_health_snapshot_timeout_handling(self):
        """Test health snapshot handles MCP call timeouts."""
        mock_client = AsyncMock(spec=MCPBridge)

        # Mock timeout on readiness call
        mock_client.call_tool = AsyncMock(side_effect=asyncio.TimeoutError())

        today = "2024-01-25"
        snapshot = await _get_health_snapshot_async(mock_client, today)

        # Should return fallback values after timeout
        assert snapshot["readiness"] == 75
        assert snapshot["sleep_score"] == 82

    @pytest.mark.asyncio
    async def test_get_health_snapshot_connection_error(self):
        """Test health snapshot handles connection errors."""
        mock_client = AsyncMock(spec=MCPBridge)

        # Mock connection error
        mock_client.call_tool = AsyncMock(side_effect=ConnectionRefusedError())

        today = "2024-01-25"
        snapshot = await _get_health_snapshot_async(mock_client, today)

        # Should return fallback values after error
        assert snapshot["readiness"] == 75
        assert snapshot["sleep_score"] == 82

    @pytest.mark.asyncio
    async def test_get_health_snapshot_with_dict_response(self):
        """Test health snapshot handles dict response format."""
        mock_client = AsyncMock(spec=MCPBridge)

        # Mock dict response (not list)
        readiness_result = ToolResult(
            success=True,
            data={"score": 88},
            error=None
        )

        sleep_result = ToolResult(
            success=True,
            data={"score": 85},
            error=None
        )

        activity_result = ToolResult(
            success=True,
            data={"steps": 9000, "active_calories": 420},
            error=None
        )

        mock_client.call_tool = AsyncMock(side_effect=[
            readiness_result,
            sleep_result,
            activity_result
        ])

        today = "2024-01-25"
        snapshot = await _get_health_snapshot_async(mock_client, today)

        # Should handle dict format correctly
        assert snapshot["readiness"] == 88
        assert snapshot["sleep_score"] == 85
        assert snapshot["activity"]["steps"] == 9000


class TestEnergyAppropriateTasks:
    """Test energy-appropriate task fetching from WorkOS."""

    @pytest.mark.asyncio
    async def test_get_tasks_for_low_energy(self):
        """Test fetching admin tasks for low energy level."""
        mock_client = AsyncMock(spec=MCPBridge)

        # Mock tasks response with mixed drain types
        tasks_result = ToolResult(
            success=True,
            data=[
                {"title": "Admin task 1", "drainType": "admin", "points": 1},
                {"title": "Deep task 1", "drainType": "deep", "points": 7},
                {"title": "Admin task 2", "drainType": "admin", "points": 1},
                {"title": "Shallow task 1", "drainType": "shallow", "points": 2},
            ],
            error=None
        )

        mock_client.call_tool = AsyncMock(return_value=tasks_result)

        tasks = await _get_energy_appropriate_tasks_async(mock_client, "low", limit=5)

        # Should only return admin tasks
        assert len(tasks) == 2
        assert all(task["drainType"] == "admin" for task in tasks)

    @pytest.mark.asyncio
    async def test_get_tasks_for_high_energy(self):
        """Test fetching deep tasks for high energy level."""
        mock_client = AsyncMock(spec=MCPBridge)

        # Mock tasks response
        tasks_result = ToolResult(
            success=True,
            data=[
                {"title": "Deep task 1", "drainType": "deep", "points": 7},
                {"title": "Admin task 1", "drainType": "admin", "points": 1},
                {"title": "Deep task 2", "drainType": "deep", "points": 5},
            ],
            error=None
        )

        mock_client.call_tool = AsyncMock(return_value=tasks_result)

        tasks = await _get_energy_appropriate_tasks_async(mock_client, "high", limit=5)

        # Should only return deep tasks
        assert len(tasks) == 2
        assert all(task["drainType"] == "deep" for task in tasks)

    @pytest.mark.asyncio
    async def test_get_tasks_with_none_client(self):
        """Test task fetching with None client returns empty list."""
        tasks = await _get_energy_appropriate_tasks_async(None, "medium", limit=5)

        # Should return empty list
        assert tasks == []

    @pytest.mark.asyncio
    async def test_get_tasks_timeout_handling(self):
        """Test task fetching handles MCP call timeouts."""
        mock_client = AsyncMock(spec=MCPBridge)

        # Mock timeout
        mock_client.call_tool = AsyncMock(side_effect=asyncio.TimeoutError())

        tasks = await _get_energy_appropriate_tasks_async(mock_client, "medium", limit=5)

        # Should return empty list after timeout
        assert tasks == []

    @pytest.mark.asyncio
    async def test_get_tasks_respects_limit(self):
        """Test that task fetching respects the limit parameter."""
        mock_client = AsyncMock(spec=MCPBridge)

        # Mock many tasks of same drain type
        tasks_result = ToolResult(
            success=True,
            data=[
                {"title": f"Shallow task {i}", "drainType": "shallow", "points": 2}
                for i in range(10)
            ],
            error=None
        )

        mock_client.call_tool = AsyncMock(return_value=tasks_result)

        tasks = await _get_energy_appropriate_tasks_async(mock_client, "medium", limit=3)

        # Should respect limit
        assert len(tasks) == 3


class TestSynchronousWrappers:
    """Test synchronous wrapper functions."""

    def test_get_health_snapshot_wrapper(self):
        """Test synchronous get_health_snapshot wrapper."""
        # Mock the async function with AsyncMock to return coroutine
        with patch('workflow._get_health_snapshot_async', new=AsyncMock()) as mock_async:
            mock_async.return_value = {
                "readiness": 80,
                "sleep_score": 85,
                "activity": {"steps": 9500},
                "stress": {"stress_high": 1}
            }

            with patch('workflow._get_oura_client', return_value=None):
                with patch('workflow._get_workos_client', return_value=None):
                    snapshot = get_health_snapshot()

                    # Should include calculated fields
                    assert "readiness" in snapshot
                    assert "energy_level" in snapshot
                    assert "energy_message" in snapshot
                    assert "suggested_tasks" in snapshot
                    assert "visual_state" in snapshot

    def test_get_energy_appropriate_tasks_wrapper(self):
        """Test synchronous get_energy_appropriate_tasks wrapper."""
        # Mock WorkOS client unavailable
        with patch('workflow._get_workos_client', return_value=None):
            tasks = get_energy_appropriate_tasks("low")

            # Should return fallback tasks
            assert len(tasks) > 0
            assert all("title" in task for task in tasks)


class TestEnergyMapping:
    """Test energy level mapping logic."""

    def test_map_high_energy(self):
        """Test mapping high readiness scores."""
        assert map_readiness_to_energy(85) == "high"
        assert map_readiness_to_energy(95) == "high"
        assert map_readiness_to_energy(100) == "high"

    def test_map_medium_energy(self):
        """Test mapping medium readiness scores."""
        assert map_readiness_to_energy(70) == "medium"
        assert map_readiness_to_energy(75) == "medium"
        assert map_readiness_to_energy(84) == "medium"

    def test_map_low_energy(self):
        """Test mapping low readiness scores."""
        assert map_readiness_to_energy(0) == "low"
        assert map_readiness_to_energy(50) == "low"
        assert map_readiness_to_energy(69) == "low"


class TestVisualStateLogic:
    """Test visual state determination logic."""

    def test_chaos_state_low_energy_morning(self):
        """Test CHAOS state for low energy in morning."""
        # Mock morning time
        from datetime import datetime
        with patch('workflow.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 25, 8, 0)
            mock_dt.hour = 8

            state = determine_visual_state("low", 65)
            assert state == "CHAOS"

    def test_focus_state_high_energy(self):
        """Test FOCUS state for high energy."""
        state = determine_visual_state("high", 90)
        assert state == "FOCUS"

    def test_balance_state_evening(self):
        """Test BALANCE state in evening."""
        from datetime import datetime
        with patch('workflow.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 25, 19, 0)
            mock_dt.hour = 19

            state = determine_visual_state("medium", 75)
            assert state == "BALANCE"


class TestWorkflowExecution:
    """Test the main workflow execution."""

    def test_execute_health_insight_success(self):
        """Test successful workflow execution."""
        # Mock the health snapshot function
        with patch('workflow.get_health_snapshot') as mock_snapshot:
            mock_snapshot.return_value = {
                "readiness": 80,
                "sleep_score": 85,
                "activity": {"steps": 9500, "active_calories": 450},
                "stress": {"stress_high": 1},
                "energy_level": "medium",
                "energy_message": "The universe grants moderate power.",
                "suggested_tasks": [
                    {"title": "Review client work", "points": 2, "valueTier": "progress", "drainType": "shallow"}
                ],
                "visual_state": "FOCUS"
            }

            result = execute_health_insight("What's my health status?")

            # Verify result structure
            assert result["success"] is True
            assert "response" in result
            assert "snapshot" in result
            assert "Readiness: 80" in result["response"]
            assert "DESTINY" in result["response"]

    def test_execute_health_insight_with_mcp_client(self):
        """Test workflow execution with custom MCP client."""
        mock_client = Mock(spec=MCPBridge)

        with patch('workflow.get_health_snapshot') as mock_snapshot:
            mock_snapshot.return_value = {
                "readiness": 85,
                "sleep_score": 90,
                "activity": {"steps": 10000, "active_calories": 500},
                "stress": {"stress_high": 0},
                "energy_level": "high",
                "energy_message": "All stones are charged. Full power available.",
                "suggested_tasks": [],
                "visual_state": "FOCUS"
            }

            result = execute_health_insight("Morning brief", mcp_client=mock_client)

            # Should succeed with custom client
            assert result["success"] is True
            assert result["snapshot"]["readiness"] == 85


class TestTimeoutConfiguration:
    """Test timeout configuration."""

    def test_timeout_constant_defined(self):
        """Test that timeout constant is properly defined."""
        assert MCP_CALL_TIMEOUT_SECONDS is not None
        assert isinstance(MCP_CALL_TIMEOUT_SECONDS, (int, float))
        assert MCP_CALL_TIMEOUT_SECONDS > 0

    @pytest.mark.asyncio
    async def test_timeout_applied_to_mcp_calls(self):
        """Test that timeout is applied to MCP calls."""
        mock_client = AsyncMock(spec=MCPBridge)

        # Create a slow async function
        async def slow_call(*args, **kwargs):
            await asyncio.sleep(10)
            return ToolResult(success=True, data=[], error=None)

        mock_client.call_tool = slow_call

        today = "2024-01-25"

        # Should timeout and use fallback values
        snapshot = await _get_health_snapshot_async(mock_client, today)

        # Verify fallback values used
        assert snapshot["readiness"] == 75
        assert snapshot["sleep_score"] == 82


class TestGracefulDegradation:
    """Test graceful degradation when MCP servers unavailable."""

    def test_fallback_tasks_low_energy(self):
        """Test fallback task suggestions for low energy."""
        with patch('workflow._get_workos_client', return_value=None):
            tasks = get_energy_appropriate_tasks("low")

            # Should return low-energy fallback tasks
            assert len(tasks) > 0
            assert all(task.get("drainType") == "admin" for task in tasks)

    def test_fallback_tasks_medium_energy(self):
        """Test fallback task suggestions for medium energy."""
        with patch('workflow._get_workos_client', return_value=None):
            tasks = get_energy_appropriate_tasks("medium")

            # Should return medium-energy fallback tasks
            assert len(tasks) > 0
            assert all(task.get("drainType") == "shallow" for task in tasks)

    def test_fallback_tasks_high_energy(self):
        """Test fallback task suggestions for high energy."""
        with patch('workflow._get_workos_client', return_value=None):
            tasks = get_energy_appropriate_tasks("high")

            # Should return high-energy fallback tasks
            assert len(tasks) > 0
            assert all(task.get("drainType") == "deep" for task in tasks)

    def test_complete_workflow_without_mcp(self):
        """Test complete workflow execution without MCP servers."""
        # Mock both clients as unavailable
        with patch('workflow._get_oura_client', return_value=None):
            with patch('workflow._get_workos_client', return_value=None):
                result = execute_health_insight("Health check")

                # Should still succeed with fallback data
                assert result["success"] is True
                assert result["snapshot"]["readiness"] == 75
                assert len(result["snapshot"]["suggested_tasks"]) > 0
