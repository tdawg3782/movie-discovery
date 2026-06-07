"""Tests for Radarr/Sonarr calendar client methods."""
import pytest
from unittest.mock import AsyncMock, patch

from app.modules.radarr.client import RadarrClient
from app.modules.sonarr.client import SonarrClient


@pytest.fixture
def radarr_client():
    return RadarrClient(url="http://localhost:7878", api_key="test_key")


@pytest.fixture
def sonarr_client():
    return SonarrClient(url="http://localhost:8989", api_key="test_key")


@pytest.mark.asyncio
async def test_radarr_get_calendar(radarr_client):
    mock_response = [{"id": 1, "title": "Movie", "tmdbId": 123}]
    with patch.object(radarr_client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await radarr_client.get_calendar("2026-06-06", "2026-06-13")

    assert result == mock_response
    mock_get.assert_called_once_with(
        "/calendar",
        {"start": "2026-06-06", "end": "2026-06-13", "unmonitored": False},
    )


@pytest.mark.asyncio
async def test_sonarr_get_calendar(sonarr_client):
    mock_response = [{"id": 1, "seriesId": 5, "seasonNumber": 2, "episodeNumber": 5}]
    with patch.object(sonarr_client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await sonarr_client.get_calendar("2026-06-06", "2026-06-13")

    assert result == mock_response
    mock_get.assert_called_once_with(
        "/calendar",
        {"start": "2026-06-06", "end": "2026-06-13", "includeSeries": True},
    )
