"""Tests for TMDB client."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.modules.discovery.tmdb_client import (
    TMDBClient,
    TMDBClientError,
    TMDBNetworkError,
    TMDBAPIError,
)


@pytest.fixture
def tmdb_client():
    return TMDBClient(api_key="test_key", base_url="https://api.test.com/3")


@pytest.fixture
def mock_response():
    """Standard mock response for trending/search endpoints."""
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


# --- Constructor Tests ---


def test_constructor_uses_provided_base_url():
    client = TMDBClient(api_key="key", base_url="https://custom.api.com")
    assert client.base_url == "https://custom.api.com"


def test_constructor_uses_config_default_when_no_base_url():
    with patch("app.modules.discovery.tmdb_client.settings") as mock_settings:
        mock_settings.tmdb_base_url = "https://config.api.com"
        client = TMDBClient(api_key="key")
        assert client.base_url == "https://config.api.com"


def test_constructor_sets_timeout():
    client = TMDBClient(api_key="key", timeout=30.0)
    assert client.timeout == 30.0


def test_constructor_default_timeout():
    client = TMDBClient(api_key="key")
    assert client.timeout == 10.0


# --- get_trending_movies Tests ---


@pytest.mark.asyncio
async def test_get_trending_movies(tmdb_client, mock_response):
    with patch.object(tmdb_client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await tmdb_client.get_trending_movies()

    mock_get.assert_called_once_with("/trending/movie/week", {"page": 1})
    assert len(result["results"]) == 1
    assert result["results"][0]["title"] == "Test Movie"


@pytest.mark.asyncio
async def test_get_trending_movies_with_page(tmdb_client, mock_response):
    with patch.object(tmdb_client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        await tmdb_client.get_trending_movies(page=3)

    mock_get.assert_called_once_with("/trending/movie/week", {"page": 3})


# --- get_trending_shows Tests ---


@pytest.mark.asyncio
async def test_get_trending_shows(tmdb_client, mock_response):
    with patch.object(tmdb_client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await tmdb_client.get_trending_shows()

    mock_get.assert_called_once_with("/trending/tv/week", {"page": 1})
    assert result["results"][0]["id"] == 123


@pytest.mark.asyncio
async def test_get_trending_shows_with_page(tmdb_client, mock_response):
    with patch.object(tmdb_client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        await tmdb_client.get_trending_shows(page=5)

    mock_get.assert_called_once_with("/trending/tv/week", {"page": 5})


# --- search Tests ---


@pytest.mark.asyncio
async def test_search(tmdb_client):
    mock_response = {
        "results": [{"id": 456, "title": "Search Result"}],
        "page": 1,
        "total_pages": 1,
        "total_results": 1,
    }

    with patch.object(tmdb_client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await tmdb_client.search("test query")

    mock_get.assert_called_once_with("/search/multi", {"query": "test query", "page": 1})
    assert result["results"][0]["title"] == "Search Result"


@pytest.mark.asyncio
async def test_search_with_page(tmdb_client):
    with patch.object(tmdb_client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {"results": [], "page": 2}
        await tmdb_client.search("query", page=2)

    mock_get.assert_called_once_with("/search/multi", {"query": "query", "page": 2})


# --- get_similar Tests ---


@pytest.mark.asyncio
async def test_get_similar_movie(tmdb_client, mock_response):
    with patch.object(tmdb_client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await tmdb_client.get_similar(123, "movie")

    mock_get.assert_called_once_with("/movie/123/similar")
    assert result["results"][0]["id"] == 123


@pytest.mark.asyncio
async def test_get_similar_tv(tmdb_client, mock_response):
    with patch.object(tmdb_client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await tmdb_client.get_similar(456, "tv")

    mock_get.assert_called_once_with("/tv/456/similar")


@pytest.mark.asyncio
async def test_get_similar_invalid_media_type(tmdb_client):
    with pytest.raises(ValueError, match="media_type must be 'movie' or 'tv'"):
        await tmdb_client.get_similar(123, "invalid")


# --- get_details Tests ---


@pytest.mark.asyncio
async def test_get_details_movie(tmdb_client):
    details = {"id": 123, "title": "Movie Title", "runtime": 120}
    with patch.object(tmdb_client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = details
        result = await tmdb_client.get_details(123, "movie")

    mock_get.assert_called_once_with("/movie/123")
    assert result["title"] == "Movie Title"


@pytest.mark.asyncio
async def test_get_details_tv(tmdb_client):
    details = {"id": 456, "name": "TV Show", "number_of_seasons": 5}
    with patch.object(tmdb_client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = details
        result = await tmdb_client.get_details(456, "tv")

    mock_get.assert_called_once_with("/tv/456")
    assert result["name"] == "TV Show"


@pytest.mark.asyncio
async def test_get_details_invalid_media_type(tmdb_client):
    with pytest.raises(ValueError, match="media_type must be 'movie' or 'tv'"):
        await tmdb_client.get_details(123, "podcast")


# --- Error Handling Tests ---


@pytest.mark.asyncio
async def test_get_handles_timeout_error(tmdb_client):
    with patch.object(tmdb_client, "_get_client", new_callable=AsyncMock) as mock_get_client:
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.TimeoutException("timeout")
        mock_get_client.return_value = mock_client

        with pytest.raises(TMDBNetworkError, match="Request timed out"):
            await tmdb_client._get("/test")


@pytest.mark.asyncio
async def test_get_handles_connect_error(tmdb_client):
    with patch.object(tmdb_client, "_get_client", new_callable=AsyncMock) as mock_get_client:
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.ConnectError("connection failed")
        mock_get_client.return_value = mock_client

        with pytest.raises(TMDBNetworkError, match="Failed to connect"):
            await tmdb_client._get("/test")


@pytest.mark.asyncio
async def test_get_handles_http_status_error(tmdb_client):
    with patch.object(tmdb_client, "_get_client", new_callable=AsyncMock) as mock_get_client:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_client.get.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=mock_response
        )
        mock_get_client.return_value = mock_client

        with pytest.raises(TMDBAPIError, match="TMDB API error 401"):
            await tmdb_client._get("/test")


# --- Context Manager Tests ---


@pytest.mark.asyncio
async def test_context_manager():
    async with TMDBClient(api_key="test", base_url="https://api.test.com") as client:
        assert client.api_key == "test"
    # Client should be closed after exiting context
    assert client._client is None or client._client.is_closed


@pytest.mark.asyncio
async def test_close_client(tmdb_client):
    # Create client
    await tmdb_client._get_client()
    assert tmdb_client._client is not None

    # Close it
    await tmdb_client.close()
    assert tmdb_client._client is None
