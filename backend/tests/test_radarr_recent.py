import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app


client = TestClient(app)


def test_get_radarr_recent():
    """GET /api/radarr/recent should return recently added movies."""
    with patch('app.modules.radarr.client.RadarrClient.get_recent') as mock:
        mock.return_value = [
            {
                "id": 1,
                "title": "Recently Added Movie",
                "tmdbId": 12345,
                "added": "2026-01-28T10:00:00Z",
                "hasFile": True
            }
        ]

        response = client.get("/api/radarr/recent")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["title"] == "Recently Added Movie"
