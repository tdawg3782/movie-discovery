"""Tests for filtered discovery endpoints."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_discover_response():
    return {
        "results": [
            {
                "id": 123,
                "title": "Test Movie",
                "overview": "A test movie",
                "poster_path": "/test.jpg",
                "release_date": "2024-01-01",
                "vote_average": 8.5,
            }
        ],
        "page": 1,
        "total_pages": 10,
        "total_results": 100,
    }


class TestDiscoverMoviesWithFilters:
    """Tests for GET /api/discover/movies with filters."""

    def test_discover_movies_with_genre(self, client, mock_discover_response):
        """Discover movies filtered by genre."""
        with patch(
            "app.modules.discovery.router.tmdb_client.discover_movies",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = mock_discover_response
            response = client.get("/api/discover/movies?genre=28")  # Action

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        # Verify filter was passed
        mock.assert_called_once()
        call_kwargs = mock.call_args[1]
        assert call_kwargs["filters"]["with_genres"] == "28"

    def test_discover_movies_with_year(self, client, mock_discover_response):
        """Discover movies filtered by year."""
        with patch(
            "app.modules.discovery.router.tmdb_client.discover_movies",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = mock_discover_response
            response = client.get("/api/discover/movies?year=2024")

        assert response.status_code == 200
        call_kwargs = mock.call_args[1]
        assert call_kwargs["filters"]["primary_release_year"] == 2024

    def test_discover_movies_with_rating(self, client, mock_discover_response):
        """Discover movies filtered by minimum rating."""
        with patch(
            "app.modules.discovery.router.tmdb_client.discover_movies",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = mock_discover_response
            response = client.get("/api/discover/movies?rating_gte=7.5")

        assert response.status_code == 200
        call_kwargs = mock.call_args[1]
        assert call_kwargs["filters"]["vote_average.gte"] == 7.5
        assert call_kwargs["filters"]["vote_count.gte"] == 50

    def test_discover_movies_with_sort(self, client, mock_discover_response):
        """Discover movies with custom sort."""
        with patch(
            "app.modules.discovery.router.tmdb_client.discover_movies",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = mock_discover_response
            response = client.get("/api/discover/movies?sort_by=vote_average.desc")

        assert response.status_code == 200
        call_kwargs = mock.call_args[1]
        assert call_kwargs["filters"]["sort_by"] == "vote_average.desc"


class TestDiscoverShowsWithFilters:
    """Tests for GET /api/discover/shows with filters."""

    def test_discover_shows_with_filters(self, client):
        """Discover TV shows with filters."""
        mock_response = {
            "results": [
                {
                    "id": 456,
                    "name": "Test Show",
                    "overview": "A test show",
                    "poster_path": "/show.jpg",
                    "first_air_date": "2023-01-01",
                    "vote_average": 9.0,
                }
            ],
            "page": 1,
            "total_pages": 5,
            "total_results": 50,
        }

        with patch(
            "app.modules.discovery.router.tmdb_client.discover_shows",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = mock_response
            response = client.get("/api/discover/shows?genre=18&year_gte=2020")

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        call_kwargs = mock.call_args[1]
        assert call_kwargs["filters"]["with_genres"] == "18"
        assert call_kwargs["filters"]["first_air_date.gte"] == "2020-01-01"
