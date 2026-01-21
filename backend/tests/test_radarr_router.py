"""Tests for Radarr router endpoints."""
import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.modules.radarr.router import get_radarr_client
from app.modules.radarr.client import RadarrClient


@pytest.fixture
def mock_radarr_client():
    """Create a mock Radarr client."""
    return AsyncMock(spec=RadarrClient)


@pytest.fixture
def client(mock_radarr_client):
    """Create test client with mocked Radarr client dependency."""
    app.dependency_overrides[get_radarr_client] = lambda: mock_radarr_client
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_get_status_available(client, mock_radarr_client):
    """Test get movie status returns available."""
    mock_radarr_client.get_status.return_value = "available"
    mock_radarr_client.lookup_movie.return_value = {"title": "Test Movie"}

    response = client.get("/api/radarr/status/123")

    assert response.status_code == 200
    data = response.json()
    assert data["tmdb_id"] == 123
    assert data["media_type"] == "movie"
    assert data["status"] == "available"
    assert data["title"] == "Test Movie"


def test_get_status_not_found(client, mock_radarr_client):
    """Test get movie status when not in library."""
    mock_radarr_client.get_status.return_value = "not_found"
    mock_radarr_client.lookup_movie.return_value = {"title": "Test Movie"}

    response = client.get("/api/radarr/status/999")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "not_found"


def test_get_status_added(client, mock_radarr_client):
    """Test get movie status when added but not downloaded."""
    mock_radarr_client.get_status.return_value = "added"
    mock_radarr_client.lookup_movie.return_value = {"title": "Test Movie"}

    response = client.get("/api/radarr/status/456")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "added"


def test_get_status_lookup_not_found(client, mock_radarr_client):
    """Test get movie status when lookup returns no movie."""
    mock_radarr_client.get_status.return_value = "not_found"
    mock_radarr_client.lookup_movie.return_value = None

    response = client.get("/api/radarr/status/999")

    assert response.status_code == 200
    data = response.json()
    assert data["title"] is None


def test_add_movie_success(client, mock_radarr_client):
    """Test adding movie to Radarr successfully."""
    mock_radarr_client.add_movie.return_value = {"title": "Test Movie", "id": 1}

    response = client.post(
        "/api/radarr/add",
        json={"tmdb_id": 123, "quality_profile_id": 2},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["message"] == "Added Test Movie to Radarr"
    assert data["tmdb_id"] == 123
    mock_radarr_client.add_movie.assert_called_once_with(
        tmdb_id=123, quality_profile_id=2
    )


def test_add_movie_success_default_quality(client, mock_radarr_client):
    """Test adding movie with default quality profile."""
    mock_radarr_client.add_movie.return_value = {"title": "Test Movie", "id": 1}

    response = client.post("/api/radarr/add", json={"tmdb_id": 123})

    assert response.status_code == 200
    mock_radarr_client.add_movie.assert_called_once_with(
        tmdb_id=123, quality_profile_id=1
    )


def test_add_movie_failure(client, mock_radarr_client):
    """Test add movie returns 400 on error."""
    mock_radarr_client.add_movie.side_effect = ValueError("Movie not found: 999")

    response = client.post("/api/radarr/add", json={"tmdb_id": 999})

    assert response.status_code == 400
    assert "Movie not found: 999" in response.json()["detail"]


def test_add_movie_no_root_folders(client, mock_radarr_client):
    """Test add movie fails when no root folders configured."""
    mock_radarr_client.add_movie.side_effect = ValueError(
        "No root folders configured in Radarr"
    )

    response = client.post("/api/radarr/add", json={"tmdb_id": 123})

    assert response.status_code == 400
    assert "No root folders configured" in response.json()["detail"]
