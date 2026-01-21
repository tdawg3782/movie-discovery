"""Tests for discovery API endpoints."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestGetTrendingMovies:
    """Tests for GET /api/discover/movies/trending."""

    def test_returns_trending_movies(self, client):
        """Should return transformed trending movies from TMDB."""
        mock_response = {
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

        with patch(
            "app.modules.discovery.router.tmdb_client.get_trending_movies",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = mock_response
            response = client.get("/api/discover/movies/trending")

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["tmdb_id"] == 123
        assert data["results"][0]["media_type"] == "movie"
        assert data["results"][0]["title"] == "Test Movie"
        assert data["page"] == 1
        assert data["total_pages"] == 10

    def test_pagination(self, client):
        """Should pass page parameter to TMDB client."""
        mock_response = {
            "results": [],
            "page": 2,
            "total_pages": 10,
            "total_results": 100,
        }

        with patch(
            "app.modules.discovery.router.tmdb_client.get_trending_movies",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = mock_response
            response = client.get("/api/discover/movies/trending?page=2")

        mock.assert_called_once_with(page=2)
        assert response.status_code == 200
        assert response.json()["page"] == 2


class TestGetTrendingShows:
    """Tests for GET /api/discover/shows/trending."""

    def test_returns_trending_shows(self, client):
        """Should return transformed trending shows from TMDB."""
        mock_response = {
            "results": [
                {
                    "id": 456,
                    "name": "Test Show",
                    "overview": "A test show",
                    "poster_path": "/show.jpg",
                    "first_air_date": "2024-02-01",
                    "vote_average": 9.0,
                }
            ],
            "page": 1,
            "total_pages": 5,
            "total_results": 50,
        }

        with patch(
            "app.modules.discovery.router.tmdb_client.get_trending_shows",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = mock_response
            response = client.get("/api/discover/shows/trending")

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["tmdb_id"] == 456
        assert data["results"][0]["media_type"] == "show"
        assert data["results"][0]["title"] == "Test Show"
        assert data["results"][0]["release_date"] == "2024-02-01"


class TestSearch:
    """Tests for GET /api/discover/search."""

    def test_search_returns_results(self, client):
        """Should return search results from TMDB."""
        mock_response = {
            "results": [
                {
                    "id": 789,
                    "title": "Search Result",
                    "media_type": "movie",
                    "overview": "Found it",
                    "poster_path": "/found.jpg",
                    "release_date": "2024-03-01",
                    "vote_average": 7.5,
                }
            ],
            "page": 1,
            "total_pages": 1,
            "total_results": 1,
        }

        with patch(
            "app.modules.discovery.router.tmdb_client.search",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = mock_response
            response = client.get("/api/discover/search?q=test")

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["tmdb_id"] == 789

    def test_search_filters_non_media(self, client):
        """Should filter out non-movie/tv results (like people)."""
        mock_response = {
            "results": [
                {"id": 1, "title": "Movie", "media_type": "movie"},
                {"id": 2, "name": "Show", "media_type": "tv"},
                {"id": 3, "name": "Actor", "media_type": "person"},
            ],
            "page": 1,
            "total_pages": 1,
            "total_results": 3,
        }

        with patch(
            "app.modules.discovery.router.tmdb_client.search",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = mock_response
            response = client.get("/api/discover/search?q=test")

        assert response.status_code == 200
        data = response.json()
        # Should only have movie and tv, not person
        assert len(data["results"]) == 2
        media_types = [r["media_type"] for r in data["results"]]
        assert "person" not in media_types

    def test_search_requires_query(self, client):
        """Should return 422 if query parameter is missing."""
        response = client.get("/api/discover/search")
        assert response.status_code == 422


class TestGetSimilar:
    """Tests for GET /api/discover/similar/{tmdb_id}."""

    def test_get_similar_movies(self, client):
        """Should return similar movies."""
        mock_response = {
            "results": [
                {
                    "id": 111,
                    "title": "Similar Movie",
                    "overview": "Like the other one",
                    "poster_path": "/similar.jpg",
                    "release_date": "2024-04-01",
                    "vote_average": 7.0,
                }
            ],
            "page": 1,
            "total_pages": 1,
            "total_results": 1,
        }

        with patch(
            "app.modules.discovery.router.tmdb_client.get_similar",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = mock_response
            response = client.get("/api/discover/similar/123?media_type=movie")

        mock.assert_called_once_with(tmdb_id=123, media_type="movie")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["media_type"] == "movie"

    def test_get_similar_shows_converts_media_type(self, client):
        """Should convert 'show' to 'tv' when calling TMDB client."""
        mock_response = {
            "results": [],
            "page": 1,
            "total_pages": 1,
            "total_results": 0,
        }

        with patch(
            "app.modules.discovery.router.tmdb_client.get_similar",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = mock_response
            response = client.get("/api/discover/similar/456?media_type=show")

        # Should convert "show" to "tv" for TMDB API
        mock.assert_called_once_with(tmdb_id=456, media_type="tv")
        assert response.status_code == 200

    def test_get_similar_requires_media_type(self, client):
        """Should return 422 if media_type is missing."""
        response = client.get("/api/discover/similar/123")
        assert response.status_code == 422
