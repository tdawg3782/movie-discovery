"""Tests for show detail endpoint."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestGetShowDetail:
    """Tests for GET /api/discover/shows/{show_id}."""

    def test_returns_show_details(self, client):
        """Should return show details with credits and videos."""
        mock_response = {
            "id": 1396,
            "name": "Breaking Bad",
            "overview": "A high school chemistry teacher turned methamphetamine producer.",
            "poster_path": "/bb.jpg",
            "backdrop_path": "/bb_bg.jpg",
            "first_air_date": "2008-01-20",
            "vote_average": 9.5,
            "genres": [{"id": 18, "name": "Drama"}, {"id": 80, "name": "Crime"}],
            "credits": {
                "cast": [
                    {"id": 17419, "name": "Bryan Cranston", "character": "Walter White"},
                ]
            },
            "videos": {
                "results": [
                    {"key": "xyz789", "site": "YouTube", "type": "Trailer"},
                ]
            },
            "recommendations": {
                "results": [
                    {"id": 60059, "name": "Better Call Saul"},
                ]
            },
        }

        with patch(
            "app.modules.discovery.router.tmdb_client.get_show_detail",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = mock_response
            response = client.get("/api/discover/shows/1396")

        mock.assert_called_once_with(1396)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1396
        assert data["name"] == "Breaking Bad"
        assert data["overview"] == "A high school chemistry teacher turned methamphetamine producer."
        assert "credits" in data
        assert "videos" in data
        assert "recommendations" in data

    def test_returns_404_for_invalid_id(self, client):
        """Should return 404 for non-existent show."""
        with patch(
            "app.modules.discovery.router.tmdb_client.get_show_detail",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = None
            response = client.get("/api/discover/shows/999999999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Show not found"
