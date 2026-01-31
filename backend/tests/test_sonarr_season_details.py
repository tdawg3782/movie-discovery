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
