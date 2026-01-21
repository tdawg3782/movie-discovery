"""Tests for Radarr client."""
import pytest
from unittest.mock import AsyncMock, patch

from app.modules.radarr.client import RadarrClient


@pytest.fixture
def client():
    return RadarrClient(url="http://localhost:7878", api_key="test_key")


@pytest.mark.asyncio
async def test_get_movie_by_tmdb_id(client):
    mock_response = [
        {"id": 1, "tmdbId": 123, "title": "Test Movie", "hasFile": True}
    ]

    with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await client.get_movie_by_tmdb_id(123)

    assert result is not None
    assert result["tmdbId"] == 123


@pytest.mark.asyncio
async def test_get_movie_not_found(client):
    with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = []
        result = await client.get_movie_by_tmdb_id(999)

    assert result is None


@pytest.mark.asyncio
async def test_add_movie(client):
    mock_lookup = [{"tmdbId": 123, "title": "Test Movie", "year": 2024}]
    mock_folders = [{"path": "/movies"}]
    mock_add = {"id": 1, "tmdbId": 123, "title": "Test Movie"}

    with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
        with patch.object(client, "_post", new_callable=AsyncMock) as mock_post:
            # First call is lookup_movie, second is rootfolder
            mock_get.side_effect = [mock_lookup, mock_folders]
            mock_post.return_value = mock_add
            result = await client.add_movie(tmdb_id=123)

    assert result["tmdbId"] == 123


@pytest.mark.asyncio
async def test_add_movie_not_found(client):
    with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = []  # lookup returns empty
        with pytest.raises(ValueError, match="Movie not found: 999"):
            await client.add_movie(tmdb_id=999)


@pytest.mark.asyncio
async def test_add_movie_no_root_folders(client):
    """Raise error when no root folders are configured."""
    mock_lookup = [{"tmdbId": 123, "title": "Test Movie", "year": 2024}]

    with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
        # First call is lookup_movie, second is rootfolder (empty)
        mock_get.side_effect = [mock_lookup, []]
        with pytest.raises(ValueError, match="No root folders configured in Radarr"):
            await client.add_movie(tmdb_id=123)


@pytest.mark.asyncio
async def test_get_status_available(client):
    mock_movie = {"id": 1, "tmdbId": 123, "hasFile": True}

    with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = [mock_movie]
        result = await client.get_status(123)

    assert result == "available"


@pytest.mark.asyncio
async def test_get_status_not_found(client):
    with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = []
        result = await client.get_status(999)

    assert result == "not_found"


@pytest.mark.asyncio
async def test_get_status_added(client):
    """Movie in library but no file yet returns 'added'."""
    mock_movie = {"id": 1, "tmdbId": 123, "hasFile": False}

    with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = [mock_movie]
        result = await client.get_status(123)

    assert result == "added"


@pytest.mark.asyncio
async def test_lookup_movie(client):
    mock_response = [{"tmdbId": 123, "title": "Test Movie"}]

    with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await client.lookup_movie(123)

    assert result is not None
    assert result["tmdbId"] == 123
    mock_get.assert_called_once_with("/movie/lookup", {"term": "tmdb:123"})


@pytest.mark.asyncio
async def test_lookup_movie_not_found(client):
    with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = []
        result = await client.lookup_movie(999)

    assert result is None
