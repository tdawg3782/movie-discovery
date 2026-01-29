import pytest
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
