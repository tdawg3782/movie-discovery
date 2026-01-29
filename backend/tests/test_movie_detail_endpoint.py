"""Tests for movie detail endpoint."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestGetMovieDetail:
    """Tests for GET /api/discover/movies/{movie_id}."""

    def test_returns_movie_details(self, client):
        """Should return movie details with credits and videos."""
        mock_response = {
            "id": 603,
            "title": "The Matrix",
            "overview": "A computer hacker learns about the true nature of reality.",
            "poster_path": "/matrix.jpg",
            "backdrop_path": "/matrix_bg.jpg",
            "release_date": "1999-03-30",
            "runtime": 136,
            "vote_average": 8.7,
            "genres": [{"id": 28, "name": "Action"}, {"id": 878, "name": "Sci-Fi"}],
            "credits": {
                "cast": [
                    {"id": 6384, "name": "Keanu Reeves", "character": "Neo"},
                ]
            },
            "videos": {
                "results": [
                    {"key": "abc123", "site": "YouTube", "type": "Trailer"},
                ]
            },
            "recommendations": {
                "results": [
                    {"id": 604, "title": "The Matrix Reloaded"},
                ]
            },
        }

        with patch(
            "app.modules.discovery.router.tmdb_client.get_movie_detail",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = mock_response
            response = client.get("/api/discover/movies/603")

        mock.assert_called_once_with(603)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 603
        assert data["title"] == "The Matrix"
        assert data["overview"] == "A computer hacker learns about the true nature of reality."
        assert "credits" in data
        assert "videos" in data
        assert "recommendations" in data

    def test_returns_404_for_invalid_id(self, client):
        """Should return 404 for non-existent movie."""
        with patch(
            "app.modules.discovery.router.tmdb_client.get_movie_detail",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = None
            response = client.get("/api/discover/movies/999999999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Movie not found"
