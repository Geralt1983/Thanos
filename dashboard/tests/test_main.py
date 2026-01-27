# dashboard/tests/test_main.py
import pytest


def test_health_endpoint(client):
    """Test /health endpoint returns 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "thanos-dashboard-api"
    }


def test_root_endpoint(client):
    """Test / endpoint returns API info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Thanos Dashboard API"
    assert data["version"] == "0.1.0"
    assert data["status"] == "operational"


def test_openapi_docs_available(client):
    """Test OpenAPI documentation is available."""
    response = client.get("/docs")
    assert response.status_code == 200
