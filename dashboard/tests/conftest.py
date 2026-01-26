# dashboard/tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def client():
    """FastAPI test client fixture."""
    from dashboard.main import app
    return TestClient(app)


@pytest.fixture(autouse=True)
def mock_mcp_client(monkeypatch):
    """Mock MCP client for testing without real MCP servers (autouse)."""
    # Create a mock MCP client instance
    mock_client = MagicMock()

    # Mock async methods with proper return values
    mock_client.get_tasks = AsyncMock(return_value=[
        {"id": "1", "title": "Test task", "points": 10, "status": "active"}
    ])

    mock_client.get_today_metrics = AsyncMock(return_value={
        "points_earned": 25,
        "daily_target": 50,
        "pace_status": "on pace",
        "streak_days": 3,
        "clients_touched": ["Orlando"],
        "tasks_completed": 2,
        "tasks_active": 5
    })

    mock_client.get_energy_logs = AsyncMock(return_value=[
        {"date": "2026-01-26", "level": "high", "note": "Good morning"}
    ])

    mock_client.get_readiness = AsyncMock(return_value=[
        {"date": "2026-01-26", "score": 85}
    ])

    mock_client.get_correlations = AsyncMock(return_value={
        "daily_data": [],
        "stats": {},
        "days_analyzed": 7
    })

    # Patch the get_client function everywhere it's used
    import dashboard.mcp_client as mcp_client_module
    import dashboard.api.tasks as tasks_module
    import dashboard.api.energy as energy_module
    import dashboard.api.health as health_module
    import dashboard.api.correlations as correlations_module

    monkeypatch.setattr(mcp_client_module, 'get_client', lambda: mock_client)
    monkeypatch.setattr(tasks_module, 'get_client', lambda: mock_client)
    monkeypatch.setattr(energy_module, 'get_client', lambda: mock_client)
    monkeypatch.setattr(health_module, 'get_client', lambda: mock_client)
    monkeypatch.setattr(correlations_module, 'get_client', lambda: mock_client)

    return mock_client
