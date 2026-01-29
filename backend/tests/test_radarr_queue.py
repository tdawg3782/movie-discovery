import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app


client = TestClient(app)


def test_get_radarr_queue():
    """GET /api/radarr/queue should return download queue."""
    with patch('app.modules.radarr.client.RadarrClient.get_queue') as mock:
        mock.return_value = {
            "records": [
                {
                    "id": 1,
                    "movieId": 123,
                    "title": "Test Movie",
                    "status": "downloading",
                    "sizeleft": 1000000000,
                    "size": 2000000000,
                    "timeleft": "01:30:00"
                }
            ],
            "totalRecords": 1
        }

        response = client.get("/api/radarr/queue")
        assert response.status_code == 200
        data = response.json()
        assert "records" in data
        assert len(data["records"]) == 1


def test_get_radarr_queue_empty():
    """GET /api/radarr/queue should handle empty queue."""
    with patch('app.modules.radarr.client.RadarrClient.get_queue') as mock:
        mock.return_value = {"records": [], "totalRecords": 0}

        response = client.get("/api/radarr/queue")
        assert response.status_code == 200
        data = response.json()
        assert data["records"] == []
