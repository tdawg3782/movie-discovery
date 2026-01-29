"""Tests for genre API endpoints."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestGetMovieGenres:
    """Tests for GET /api/genres/movies."""

    def test_get_movie_genres(self, client):
        """GET /api/genres/movies should return genre list."""
        mock_response = {
            "genres": [
                {"id": 28, "name": "Action"},
                {"id": 12, "name": "Adventure"},
                {"id": 35, "name": "Comedy"},
            ]
        }

        with patch(
            "app.modules.discovery.router.tmdb_client.get_movie_genres",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = mock_response
            response = client.get("/api/genres/movies")

        assert response.status_code == 200
        data = response.json()
        assert "genres" in data
        assert isinstance(data["genres"], list)
        assert len(data["genres"]) == 3
        assert data["genres"][0]["id"] == 28
        assert data["genres"][0]["name"] == "Action"


class TestGetTvGenres:
    """Tests for GET /api/genres/shows."""

    def test_get_tv_genres(self, client):
        """GET /api/genres/shows should return genre list."""
        mock_response = {
            "genres": [
                {"id": 10759, "name": "Action & Adventure"},
                {"id": 18, "name": "Drama"},
            ]
        }

        with patch(
            "app.modules.discovery.router.tmdb_client.get_tv_genres",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = mock_response
            response = client.get("/api/genres/shows")

        assert response.status_code == 200
        data = response.json()
        assert "genres" in data
        assert isinstance(data["genres"], list)
        assert len(data["genres"]) == 2
