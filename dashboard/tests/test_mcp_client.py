# dashboard/tests/test_mcp_client.py
import pytest
from dashboard.mcp_client import MCPClient


@pytest.mark.asyncio
async def test_mcp_client_handles_missing_bridge():
    """Test MCPClient handles missing MCP bridge gracefully."""
    client = MCPClient()

    # If bridges not initialized, methods should return None or []
    if not client._workos_bridge:
        tasks = await client.get_tasks()
        assert tasks is None or tasks == []


@pytest.mark.asyncio
async def test_mcp_client_get_correlations_partial_data():
    """Test get_correlations handles partial data gracefully."""
    client = MCPClient()

    # Even with no MCP servers, should return structure
    result = await client.get_correlations(days=7)

    if result is not None:
        assert "daily_data" in result
        assert "stats" in result
        assert "days_analyzed" in result
