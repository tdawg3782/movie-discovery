"""Tests for Sonarr client."""
import pytest
from unittest.mock import AsyncMock, patch

from app.modules.sonarr.client import SonarrClient


@pytest.fixture
def client():
    return SonarrClient(url="http://localhost:8989", api_key="test_key")


@pytest.mark.asyncio
async def test_get_series_by_tvdb_id(client):
    """Get series from library by TVDB ID."""
    # Server-side filtering returns only matching series
    mock_response = [{"id": 1, "tvdbId": 456, "title": "Test Series"}]

    with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await client.get_series_by_tvdb_id(456)

    assert result is not None
    assert result["tvdbId"] == 456
    assert result["title"] == "Test Series"
    mock_get.assert_called_once_with("/series", {"tvdbId": 456})


@pytest.mark.asyncio
async def test_get_series_not_found(client):
    """Returns None when series not in library."""
    # Server-side filtering returns empty list when not found
    with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = []
        result = await client.get_series_by_tvdb_id(999)

    assert result is None
    mock_get.assert_called_once_with("/series", {"tvdbId": 999})


@pytest.mark.asyncio
async def test_add_series(client):
    """Add series with mocked lookup and post."""
    mock_lookup = [{"tvdbId": 456, "title": "Test Series", "year": 2024}]
    mock_folders = [{"path": "/tv"}]
    mock_add = {"id": 1, "tvdbId": 456, "title": "Test Series"}

    with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
        with patch.object(client, "_post", new_callable=AsyncMock) as mock_post:
            # First call is lookup_series, second is rootfolder
            mock_get.side_effect = [mock_lookup, mock_folders]
            mock_post.return_value = mock_add
            result = await client.add_series(tmdb_id=123)

    assert result["tvdbId"] == 456
    mock_post.assert_called_once()
    # Verify the posted data has correct structure
    posted_data = mock_post.call_args[0][1]
    assert posted_data["qualityProfileId"] == 1
    assert posted_data["rootFolderPath"] == "/tv"
    assert posted_data["monitored"] is True
    assert posted_data["addOptions"] == {"searchForMissingEpisodes": True}


@pytest.mark.asyncio
async def test_add_series_not_found(client):
    """Raises error when series not found."""
    with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = []  # lookup returns empty
        with pytest.raises(ValueError, match="Series not found: 999"):
            await client.add_series(tmdb_id=999)


@pytest.mark.asyncio
async def test_add_series_no_root_folders(client):
    """Raises error when no root folders configured."""
    mock_lookup = [{"tvdbId": 456, "title": "Test Series", "year": 2024}]

    with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
        # First call is lookup_series, second is rootfolder (empty)
        mock_get.side_effect = [mock_lookup, []]
        with pytest.raises(ValueError, match="No root folders configured in Sonarr"):
            await client.add_series(tmdb_id=123)


@pytest.mark.asyncio
async def test_get_status_available(client):
    """100% episodes means available."""
    mock_lookup = [{"tvdbId": 456, "title": "Test Series"}]
    mock_series = [
        {
            "id": 1,
            "tvdbId": 456,
            "title": "Test Series",
            "statistics": {"percentOfEpisodes": 100},
        }
    ]

    with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
        # First call is lookup_series, second is filtered series query
        mock_get.side_effect = [mock_lookup, mock_series]
        result = await client.get_status(123)

    assert result == "available"


@pytest.mark.asyncio
async def test_get_status_added(client):
    """Series exists but not fully available."""
    mock_lookup = [{"tvdbId": 456, "title": "Test Series"}]
    mock_series = [
        {
            "id": 1,
            "tvdbId": 456,
            "title": "Test Series",
            "statistics": {"percentOfEpisodes": 50},
        }
    ]

    with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
        # First call is lookup_series, second is filtered series query
        mock_get.side_effect = [mock_lookup, mock_series]
        result = await client.get_status(123)

    assert result == "added"


@pytest.mark.asyncio
async def test_get_status_not_found(client):
    """Series not in library."""
    mock_lookup = [{"tvdbId": 456, "title": "Test Series"}]
    mock_series = []  # No series in library

    with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = [mock_lookup, mock_series]
        result = await client.get_status(123)

    assert result == "not_found"


@pytest.mark.asyncio
async def test_get_status_lookup_not_found(client):
    """Series not found in lookup."""
    with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = []  # lookup returns empty
        result = await client.get_status(999)

    assert result == "not_found"


@pytest.mark.asyncio
async def test_lookup_series(client):
    """Lookup series found case."""
    mock_response = [{"tvdbId": 456, "title": "Test Series"}]

    with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await client.lookup_series(123)

    assert result is not None
    assert result["tvdbId"] == 456
    mock_get.assert_called_once_with("/series/lookup", {"term": "tmdb:123"})


@pytest.mark.asyncio
async def test_lookup_series_not_found(client):
    """Lookup series not found case."""
    with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = []
        result = await client.lookup_series(999)

    assert result is None
