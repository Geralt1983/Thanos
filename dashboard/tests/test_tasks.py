# dashboard/tests/test_tasks.py
import pytest


def test_get_tasks_with_valid_status(client, mock_mcp_client):
    """Test GET /api/tasks with valid status parameter."""
    response = client.get("/api/tasks?status=active")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "tasks" in data["data"]


def test_get_tasks_with_invalid_status(client):
    """Test GET /api/tasks with invalid status returns 400."""
    response = client.get("/api/tasks?status=invalid")
    assert response.status_code == 400
    assert "Invalid status" in response.json()["detail"]


def test_get_tasks_applies_limit(client, mock_mcp_client):
    """Test GET /api/tasks respects limit parameter."""
    response = client.get("/api/tasks?status=active&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["filters"]["limit"] == 5


def test_get_today_metrics(client, mock_mcp_client):
    """Test GET /api/tasks/metrics."""
    response = client.get("/api/tasks/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "points_earned" in data["data"]
    assert "daily_target" in data["data"]
