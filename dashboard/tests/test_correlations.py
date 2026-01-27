# dashboard/tests/test_correlations.py
import pytest


def test_get_correlations_with_valid_days(client, mock_mcp_client):
    """Test GET /api/correlations with valid days parameter."""
    response = client.get("/api/correlations?days=7")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "daily_data" in data["data"]
    assert "stats" in data["data"]


def test_get_correlations_validates_days_range(client):
    """Test GET /api/correlations validates days parameter range."""
    response = client.get("/api/correlations?days=0")
    assert response.status_code == 422

    response = client.get("/api/correlations?days=91")
    assert response.status_code == 422
