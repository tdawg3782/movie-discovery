import pytest
import httpx
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app


client = TestClient(app)


def test_get_library_activity():
    """GET /api/library/activity should return combined activity."""
    with patch('app.modules.radarr.client.RadarrClient.get_recent') as mock_radarr:
        with patch('app.modules.sonarr.client.SonarrClient.get_recent') as mock_sonarr:
            mock_radarr.return_value = [
                {"id": 1, "title": "Movie", "added": "2026-01-28T10:00:00Z", "tmdbId": 123}
            ]
            mock_sonarr.return_value = [
                {"id": 2, "title": "Show", "added": "2026-01-28T11:00:00Z", "tvdbId": 456}
            ]

            response = client.get("/api/library/activity")
            assert response.status_code == 200
            data = response.json()
            assert "movies" in data
            assert "shows" in data


def test_activity_sonarr_down_serves_partial():
    """Sonarr unreachable -> 200, movies present, shows empty, degraded=['sonarr']."""
    with patch('app.modules.radarr.client.RadarrClient.get_recent') as mock_radarr:
        with patch('app.modules.sonarr.client.SonarrClient.get_recent') as mock_sonarr:
            mock_radarr.return_value = [
                {"id": 1, "title": "Movie", "added": "2026-01-28T10:00:00Z", "tmdbId": 123}
            ]
            mock_sonarr.side_effect = httpx.ConnectError("boom")

            response = client.get("/api/library/activity")
            assert response.status_code == 200
            data = response.json()
            assert len(data["movies"]) == 1
            assert data["shows"] == []
            assert data["degraded"] == ["sonarr"]


def test_activity_radarr_down_serves_partial():
    """Radarr unreachable -> 200, shows present, movies empty, degraded=['radarr']."""
    with patch('app.modules.radarr.client.RadarrClient.get_recent') as mock_radarr:
        with patch('app.modules.sonarr.client.SonarrClient.get_recent') as mock_sonarr:
            mock_radarr.side_effect = httpx.ConnectError("boom")
            mock_sonarr.return_value = [
                {"id": 2, "title": "Show", "added": "2026-01-28T11:00:00Z", "tvdbId": 456}
            ]

            response = client.get("/api/library/activity")
            assert response.status_code == 200
            data = response.json()
            assert data["movies"] == []
            assert len(data["shows"]) == 1
            assert data["degraded"] == ["radarr"]


def test_activity_healthy_degraded_empty():
    """Both sources healthy -> degraded == []."""
    with patch('app.modules.radarr.client.RadarrClient.get_recent') as mock_radarr:
        with patch('app.modules.sonarr.client.SonarrClient.get_recent') as mock_sonarr:
            mock_radarr.return_value = []
            mock_sonarr.return_value = []

            response = client.get("/api/library/activity")
            assert response.status_code == 200
            assert response.json()["degraded"] == []


def test_queue_sonarr_down_serves_partial():
    """Sonarr queue unreachable -> 200, movies present, shows empty, degraded=['sonarr']."""
    with patch('app.modules.radarr.client.RadarrClient.get_queue') as mock_radarr:
        with patch('app.modules.sonarr.client.SonarrClient.get_queue') as mock_sonarr:
            mock_radarr.return_value = {"records": [{"id": 1, "title": "Movie"}]}
            mock_sonarr.side_effect = httpx.ConnectError("boom")

            response = client.get("/api/library/queue")
            assert response.status_code == 200
            data = response.json()
            assert len(data["movies"]) == 1
            assert data["shows"] == []
            assert data["degraded"] == ["sonarr"]


def test_queue_healthy_degraded_empty():
    """Both queue sources healthy -> degraded == []."""
    with patch('app.modules.radarr.client.RadarrClient.get_queue') as mock_radarr:
        with patch('app.modules.sonarr.client.SonarrClient.get_queue') as mock_sonarr:
            mock_radarr.return_value = {"records": []}
            mock_sonarr.return_value = {"records": []}

            response = client.get("/api/library/queue")
            assert response.status_code == 200
            assert response.json()["degraded"] == []
