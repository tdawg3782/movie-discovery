"""Tests for Settings API router."""
import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db


@pytest.fixture(autouse=True)
def setup_database():
    """Ensure database is initialized before tests."""
    os.makedirs("data", exist_ok=True)
    init_db()


client = TestClient(app)


def test_get_settings():
    """GET /api/settings should return settings."""
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert "has_tmdb" in data
    assert "has_radarr" in data
    assert "has_sonarr" in data


def test_update_settings():
    """PUT /api/settings should update settings."""
    response = client.put(
        "/api/settings",
        json={"tmdb_api_key": "test-key-for-router"}
    )
    assert response.status_code == 200

    # Verify it was saved
    response = client.get("/api/settings")
    data = response.json()
    assert data["has_tmdb"] is True


def test_test_connection_invalid_service():
    """POST /api/settings/test with invalid service should fail."""
    response = client.post(
        "/api/settings/test",
        json={"service": "invalid"}
    )
    assert response.status_code == 422
