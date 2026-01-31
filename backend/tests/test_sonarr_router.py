"""Tests for Sonarr router endpoints."""
import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.modules.sonarr.router import get_sonarr_client
from app.modules.sonarr.client import SonarrClient


@pytest.fixture
def mock_sonarr_client():
    """Create a mock Sonarr client."""
    return AsyncMock(spec=SonarrClient)


@pytest.fixture
def client(mock_sonarr_client):
    """Create test client with mocked Sonarr client dependency."""
    app.dependency_overrides[get_sonarr_client] = lambda: mock_sonarr_client
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_get_status_available(client, mock_sonarr_client):
    """Test get series status returns available."""
    mock_sonarr_client.get_status.return_value = "available"
    mock_sonarr_client.lookup_series.return_value = {"title": "Test Series"}

    response = client.get("/api/sonarr/status/123")

    assert response.status_code == 200
    data = response.json()
    assert data["tmdb_id"] == 123
    assert data["media_type"] == "show"
    assert data["status"] == "available"
    assert data["title"] == "Test Series"


def test_get_status_not_found(client, mock_sonarr_client):
    """Test get series status when not in library."""
    mock_sonarr_client.get_status.return_value = "not_found"
    mock_sonarr_client.lookup_series.return_value = {"title": "Test Series"}

    response = client.get("/api/sonarr/status/999")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "not_found"


def test_get_status_added(client, mock_sonarr_client):
    """Test get series status when added but not fully downloaded."""
    mock_sonarr_client.get_status.return_value = "added"
    mock_sonarr_client.lookup_series.return_value = {"title": "Test Series"}

    response = client.get("/api/sonarr/status/456")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "added"


def test_get_status_lookup_not_found(client, mock_sonarr_client):
    """Test get series status when lookup returns no series."""
    mock_sonarr_client.get_status.return_value = "not_found"
    mock_sonarr_client.lookup_series.return_value = None

    response = client.get("/api/sonarr/status/999")

    assert response.status_code == 200
    data = response.json()
    assert data["title"] is None


def test_add_series_success(client, mock_sonarr_client):
    """Test adding series to Sonarr successfully."""
    mock_sonarr_client.add_series.return_value = {"title": "Test Series", "id": 1}

    response = client.post(
        "/api/sonarr/add",
        json={"tmdb_id": 123, "quality_profile_id": 2},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["message"] == "Added Test Series to Sonarr"
    assert data["tmdb_id"] == 123
    mock_sonarr_client.add_series.assert_called_once_with(
        tmdb_id=123, quality_profile_id=2
    )


def test_add_series_success_default_quality(client, mock_sonarr_client):
    """Test adding series with default quality profile (resolved by client)."""
    mock_sonarr_client.add_series.return_value = {"title": "Test Series", "id": 1}

    response = client.post("/api/sonarr/add", json={"tmdb_id": 123})

    assert response.status_code == 200
    # Router passes None, client resolves default quality profile
    mock_sonarr_client.add_series.assert_called_once_with(
        tmdb_id=123, quality_profile_id=None
    )


def test_add_series_failure(client, mock_sonarr_client):
    """Test add series returns 400 on error."""
    mock_sonarr_client.add_series.side_effect = ValueError("Series not found: 999")

    response = client.post("/api/sonarr/add", json={"tmdb_id": 999})

    assert response.status_code == 400
    assert "Series not found: 999" in response.json()["detail"]


def test_add_series_no_root_folders(client, mock_sonarr_client):
    """Test add series fails when no root folders configured."""
    mock_sonarr_client.add_series.side_effect = ValueError(
        "No root folders configured in Sonarr"
    )

    response = client.post("/api/sonarr/add", json={"tmdb_id": 123})

    assert response.status_code == 400
    assert "No root folders configured" in response.json()["detail"]
