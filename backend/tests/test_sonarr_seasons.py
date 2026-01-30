"""Tests for Sonarr client season selection."""
import pytest
from unittest.mock import AsyncMock, patch

from app.modules.sonarr.client import SonarrClient


@pytest.fixture
def client():
    return SonarrClient(url="http://localhost:8989", api_key="test_key")


@pytest.mark.asyncio
async def test_add_series_with_selected_seasons(client):
    """Sonarr client sets season monitoring based on selection."""
    mock_lookup = [{
        "title": "Test Show",
        "tvdbId": 12345,
        "seasons": [
            {"seasonNumber": 0, "monitored": False},
            {"seasonNumber": 1, "monitored": True},
            {"seasonNumber": 2, "monitored": True},
            {"seasonNumber": 3, "monitored": True},
        ]
    }]
    mock_folders = [{"path": "/tv"}]
    mock_profiles = [{"id": 1}]
    mock_add = {"id": 1, "title": "Test Show"}

    with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
        with patch.object(client, "_post", new_callable=AsyncMock) as mock_post:
            # Calls: lookup_series, get_series_by_tvdb_id, rootfolder, qualityprofile
            mock_get.side_effect = [
                mock_lookup,           # lookup_series
                [],                    # get_series_by_tvdb_id (not in library)
                mock_folders,          # rootfolder
                mock_profiles,         # qualityprofile
            ]
            mock_post.return_value = mock_add

            await client.add_series(tmdb_id=12345, selected_seasons=[1, 3])

            # Verify the posted data has correct season monitoring
            posted_data = mock_post.call_args[0][1]
            seasons = {s["seasonNumber"]: s["monitored"] for s in posted_data["seasons"]}

            assert seasons[0] is False  # Specials never monitored
            assert seasons[1] is True   # Selected
            assert seasons[2] is False  # Not selected
            assert seasons[3] is True   # Selected


@pytest.mark.asyncio
async def test_add_series_without_selected_seasons_monitors_all(client):
    """Without selected_seasons, all seasons remain as lookup returned them."""
    mock_lookup = [{
        "title": "Test Show",
        "tvdbId": 12345,
        "seasons": [
            {"seasonNumber": 0, "monitored": False},
            {"seasonNumber": 1, "monitored": True},
            {"seasonNumber": 2, "monitored": True},
        ]
    }]
    mock_folders = [{"path": "/tv"}]
    mock_profiles = [{"id": 1}]
    mock_add = {"id": 1, "title": "Test Show"}

    with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
        with patch.object(client, "_post", new_callable=AsyncMock) as mock_post:
            mock_get.side_effect = [
                mock_lookup,
                [],
                mock_folders,
                mock_profiles,
            ]
            mock_post.return_value = mock_add

            # No selected_seasons - should use lookup defaults
            await client.add_series(tmdb_id=12345)

            posted_data = mock_post.call_args[0][1]
            seasons = {s["seasonNumber"]: s["monitored"] for s in posted_data["seasons"]}

            # All seasons keep their original monitored state from lookup
            assert seasons[0] is False
            assert seasons[1] is True
            assert seasons[2] is True


@pytest.mark.asyncio
async def test_add_series_selected_seasons_empty_list(client):
    """Empty selected_seasons list means no seasons monitored (except specials stay False)."""
    mock_lookup = [{
        "title": "Test Show",
        "tvdbId": 12345,
        "seasons": [
            {"seasonNumber": 0, "monitored": False},
            {"seasonNumber": 1, "monitored": True},
            {"seasonNumber": 2, "monitored": True},
        ]
    }]
    mock_folders = [{"path": "/tv"}]
    mock_profiles = [{"id": 1}]
    mock_add = {"id": 1, "title": "Test Show"}

    with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
        with patch.object(client, "_post", new_callable=AsyncMock) as mock_post:
            mock_get.side_effect = [
                mock_lookup,
                [],
                mock_folders,
                mock_profiles,
            ]
            mock_post.return_value = mock_add

            # Empty list = monitor nothing
            await client.add_series(tmdb_id=12345, selected_seasons=[])

            posted_data = mock_post.call_args[0][1]
            seasons = {s["seasonNumber"]: s["monitored"] for s in posted_data["seasons"]}

            assert seasons[0] is False
            assert seasons[1] is False
            assert seasons[2] is False


@pytest.mark.asyncio
async def test_add_series_selected_seasons_specials_ignored(client):
    """Even if season 0 is in selected_seasons, it should not be monitored."""
    mock_lookup = [{
        "title": "Test Show",
        "tvdbId": 12345,
        "seasons": [
            {"seasonNumber": 0, "monitored": False},
            {"seasonNumber": 1, "monitored": True},
        ]
    }]
    mock_folders = [{"path": "/tv"}]
    mock_profiles = [{"id": 1}]
    mock_add = {"id": 1, "title": "Test Show"}

    with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
        with patch.object(client, "_post", new_callable=AsyncMock) as mock_post:
            mock_get.side_effect = [
                mock_lookup,
                [],
                mock_folders,
                mock_profiles,
            ]
            mock_post.return_value = mock_add

            # Try to select season 0 (specials) - should be ignored
            await client.add_series(tmdb_id=12345, selected_seasons=[0, 1])

            posted_data = mock_post.call_args[0][1]
            seasons = {s["seasonNumber"]: s["monitored"] for s in posted_data["seasons"]}

            assert seasons[0] is False  # Still False despite being in selection
            assert seasons[1] is True
