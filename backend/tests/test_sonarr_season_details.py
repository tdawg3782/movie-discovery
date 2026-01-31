# backend/tests/test_sonarr_season_details.py
"""Tests for Sonarr season details."""
import pytest
from unittest.mock import AsyncMock, patch
from app.modules.sonarr.client import SonarrClient


@pytest.fixture
def client():
    return SonarrClient(url="http://localhost:8989", api_key="test_key")


@pytest.mark.asyncio
async def test_get_series_details_returns_season_status(client):
    """Get series details with season-level status."""
    mock_lookup = [{"tvdbId": 81189, "title": "Breaking Bad"}]
    mock_series = {
        "id": 1,
        "title": "Breaking Bad",
        "tvdbId": 81189,
        "seasons": [
            {"seasonNumber": 1, "monitored": True, "statistics": {"percentOfEpisodes": 100, "episodeCount": 7, "episodeFileCount": 7}},
            {"seasonNumber": 2, "monitored": True, "statistics": {"percentOfEpisodes": 50, "episodeCount": 13, "episodeFileCount": 6}},
            {"seasonNumber": 3, "monitored": False, "statistics": {"percentOfEpisodes": 0, "episodeCount": 13, "episodeFileCount": 0}},
        ]
    }

    with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = [mock_lookup, [mock_series]]
        result = await client.get_series_details(tmdb_id=1396)

    assert result is not None
    assert result["in_library"] is True
    assert result["sonarr_id"] == 1
    assert len(result["seasons"]) == 3
    assert result["seasons"][0]["status"] == "downloaded"
    assert result["seasons"][1]["status"] == "monitored"
    assert result["seasons"][2]["status"] == "available"


@pytest.mark.asyncio
async def test_get_series_details_not_in_library(client):
    """Returns None when series not in Sonarr library."""
    mock_lookup = [{"tvdbId": 81189, "title": "Breaking Bad"}]

    with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = [mock_lookup, []]  # Empty library result
        result = await client.get_series_details(tmdb_id=1396)

    assert result is None


@pytest.mark.asyncio
async def test_update_season_monitoring(client):
    """Update monitoring for additional seasons."""
    mock_lookup = [{"tvdbId": 81189}]
    mock_existing = {
        "id": 1,
        "title": "Breaking Bad",
        "tvdbId": 81189,
        "seasons": [
            {"seasonNumber": 1, "monitored": True},
            {"seasonNumber": 2, "monitored": False},
            {"seasonNumber": 3, "monitored": False},
        ]
    }
    mock_updated = {**mock_existing, "seasons": [
        {"seasonNumber": 1, "monitored": True},
        {"seasonNumber": 2, "monitored": True},  # Now monitored
        {"seasonNumber": 3, "monitored": False},
    ]}

    with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
        with patch.object(client, "_put", new_callable=AsyncMock) as mock_put:
            with patch.object(client, "_post", new_callable=AsyncMock) as mock_post:
                mock_get.side_effect = [mock_lookup, [mock_existing]]
                mock_put.return_value = mock_updated
                mock_post.return_value = {"id": 123}  # Command response

                result = await client.update_season_monitoring(tmdb_id=1396, seasons_to_add=[2])

    assert result["seasons"][1]["monitored"] is True
    mock_put.assert_called_once()
    mock_post.assert_called_once()  # Search command
