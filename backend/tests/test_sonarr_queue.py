import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app


client = TestClient(app)


def test_get_sonarr_queue():
    """GET /api/sonarr/queue should return download queue."""
    with patch('app.modules.sonarr.client.SonarrClient.get_queue') as mock:
        mock.return_value = {
            "records": [
                {
                    "id": 1,
                    "seriesId": 456,
                    "title": "Test Show S01E01",
                    "status": "downloading",
                    "sizeleft": 500000000,
                    "size": 1000000000,
                    "timeleft": "00:45:00"
                }
            ],
            "totalRecords": 1
        }

        response = client.get("/api/sonarr/queue")
        assert response.status_code == 200
        data = response.json()
        assert "records" in data
