"""Tests for TMDB client."""
import pytest
from unittest.mock import AsyncMock, patch

from app.modules.discovery.tmdb_client import TMDBClient


@pytest.fixture
def tmdb_client():
    return TMDBClient(api_key="test_key")


@pytest.mark.asyncio
async def test_get_trending_movies(tmdb_client):
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

    with patch.object(tmdb_client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await tmdb_client.get_trending_movies()

    assert len(result["results"]) == 1
    assert result["results"][0]["title"] == "Test Movie"


@pytest.mark.asyncio
async def test_search_movies(tmdb_client):
    mock_response = {
        "results": [{"id": 456, "title": "Search Result"}],
        "page": 1,
        "total_pages": 1,
        "total_results": 1,
    }

    with patch.object(tmdb_client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await tmdb_client.search("test query")

    mock_get.assert_called_once()
    assert result["results"][0]["title"] == "Search Result"
