"""Tests for Sonarr seasons endpoint."""
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


def test_get_series_seasons(client, mock_sonarr_client):
    """Get season status for a series."""
    mock_sonarr_client.get_series_details.return_value = {
        "in_library": True,
        "sonarr_id": 1,
        "title": "Breaking Bad",
        "seasons": [
            {"number": 1, "status": "downloaded", "episodes": "7/7"},
            {"number": 2, "status": "available", "episodes": "0/13"},
        ]
    }

    response = client.get("/api/sonarr/series/1396/seasons")

    assert response.status_code == 200
    data = response.json()
    assert data["in_library"] is True
    assert len(data["seasons"]) == 2


def test_get_series_seasons_not_in_library(client, mock_sonarr_client):
    """Returns 404 when series not in library."""
    mock_sonarr_client.get_series_details.return_value = None

    response = client.get("/api/sonarr/series/99999/seasons")

    assert response.status_code == 404
