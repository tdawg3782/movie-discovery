import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app


client = TestClient(app)


def test_get_sonarr_recent():
    """GET /api/sonarr/recent should return recently added shows."""
    with patch('app.modules.sonarr.client.SonarrClient.get_recent') as mock:
        mock.return_value = [
            {
                "id": 1,
                "title": "Recently Added Show",
                "tvdbId": 67890,
                "added": "2026-01-28T10:00:00Z"
            }
        ]

        response = client.get("/api/sonarr/recent")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
