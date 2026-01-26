# dashboard/tests/test_health.py
import pytest


def test_get_readiness_with_valid_days(client, mock_mcp_client):
    """Test GET /api/health/readiness with valid days parameter."""
    response = client.get("/api/health/readiness?days=7")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "readiness" in data["data"]


def test_get_readiness_validates_days_range(client):
    """Test GET /api/health/readiness validates days parameter range."""
    # Test below minimum
    response = client.get("/api/health/readiness?days=0")
    assert response.status_code == 422

    # Test above maximum
    response = client.get("/api/health/readiness?days=91")
    assert response.status_code == 422
