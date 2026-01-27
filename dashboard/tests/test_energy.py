# dashboard/tests/test_energy.py
import pytest


def test_get_energy_with_valid_days(client, mock_mcp_client):
    """Test GET /api/energy with valid days parameter."""
    response = client.get("/api/energy?days=7")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "energy_logs" in data["data"]


def test_get_energy_validates_days_range(client):
    """Test GET /api/energy validates days parameter range."""
    # Test below minimum
    response = client.get("/api/energy?days=0")
    assert response.status_code == 422  # Pydantic validation error

    # Test above maximum
    response = client.get("/api/energy?days=91")
    assert response.status_code == 422


def test_get_energy_default_days(client, mock_mcp_client):
    """Test GET /api/energy uses default days=7."""
    response = client.get("/api/energy")
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["filters"]["days"] == 7
