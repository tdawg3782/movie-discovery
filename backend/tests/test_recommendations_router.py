"""Tests for the For You recommendations aggregating endpoint."""
import logging
import types

import httpx
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app
from app.modules.radarr.router import get_radarr_client
from app.modules.sonarr.router import get_sonarr_client
from app.modules.watchlist.router import get_service
from app.modules.radarr.client import RadarrClient
from app.modules.sonarr.client import SonarrClient
from app.modules.recommendations.router import reset_cache
from app.modules.discovery.tmdb_client import TMDBNetworkError


class FakeWatchlistService:
    """Minimal stand-in exposing get_all()."""

    def __init__(self, rows):
        self._rows = rows

    def get_all(self):
        return self._rows


@pytest.fixture
def mock_radarr():
    return AsyncMock(spec=RadarrClient)


@pytest.fixture
def mock_sonarr():
    return AsyncMock(spec=SonarrClient)


@pytest.fixture
def watchlist_rows():
    """Mutable list of fake watchlist rows the fake service returns."""
    return []


@pytest.fixture
def client(mock_radarr, mock_sonarr, watchlist_rows):
    reset_cache()
    app.dependency_overrides[get_radarr_client] = lambda: mock_radarr
    app.dependency_overrides[get_sonarr_client] = lambda: mock_sonarr
    app.dependency_overrides[get_service] = lambda: FakeWatchlistService(watchlist_rows)
    yield TestClient(app)
    app.dependency_overrides.clear()
    reset_cache()


def test_empty_local_data_returns_empty_and_no_tmdb_calls(client, mock_radarr, mock_sonarr):
    """No watchlist and empty arr libraries -> empty results, TMDB never called."""
    mock_radarr.get_all_movies.return_value = []
    mock_sonarr.get_all_series.return_value = []

    with patch(
        "app.modules.clients.tmdb_client.get_recommendations",
        new_callable=AsyncMock,
    ) as mock_get_recs:
        mock_get_recs.return_value = {
            "results": [{"id": 9, "title": "Rec", "vote_average": 7.0, "popularity": 10}]
        }
        response = client.get("/api/for-you")

    assert response.status_code == 200
    assert response.json()["results"] == []
    mock_get_recs.assert_not_called()


def test_watchlist_seed_returns_recs_excluding_seed(
    client, mock_radarr, mock_sonarr, watchlist_rows
):
    """A watchlisted seed yields recs, but the seed itself is excluded from output."""
    watchlist_rows.append(types.SimpleNamespace(tmdb_id=5, media_type="movie"))
    mock_radarr.get_all_movies.return_value = []
    mock_sonarr.get_all_series.return_value = []

    with patch(
        "app.modules.clients.tmdb_client.get_recommendations",
        new_callable=AsyncMock,
    ) as mock_get_recs:
        mock_get_recs.return_value = {
            "results": [
                {"id": 5, "title": "Seed", "vote_average": 8.0, "popularity": 20},
                {"id": 9, "title": "Rec", "vote_average": 7.0, "popularity": 10},
            ]
        }
        response = client.get("/api/for-you")

    assert response.status_code == 200
    ids = [r["tmdb_id"] for r in response.json()["results"]]
    assert 9 in ids
    assert 5 not in ids


def test_owned_movie_excluded_even_if_recommended(
    client, mock_radarr, mock_sonarr, watchlist_rows
):
    """A recommended title already owned in Radarr is excluded from output."""
    watchlist_rows.append(types.SimpleNamespace(tmdb_id=5, media_type="movie"))
    mock_radarr.get_all_movies.return_value = [{"tmdbId": 9}]
    mock_sonarr.get_all_series.return_value = []

    with patch(
        "app.modules.clients.tmdb_client.get_recommendations",
        new_callable=AsyncMock,
    ) as mock_get_recs:
        mock_get_recs.return_value = {
            "results": [{"id": 9, "title": "Rec", "vote_average": 7.0, "popularity": 10}]
        }
        response = client.get("/api/for-you")

    assert response.status_code == 200
    ids = [r["tmdb_id"] for r in response.json()["results"]]
    assert 9 not in ids


def test_arr_down_still_returns_watchlist_recs(
    client, mock_radarr, mock_sonarr, watchlist_rows
):
    """Arr clients raising still yields watchlist-seeded recommendations (best-effort)."""
    watchlist_rows.append(types.SimpleNamespace(tmdb_id=5, media_type="movie"))
    mock_radarr.get_all_movies.side_effect = Exception("down")
    mock_sonarr.get_all_series.side_effect = Exception("down")

    with patch(
        "app.modules.clients.tmdb_client.get_recommendations",
        new_callable=AsyncMock,
    ) as mock_get_recs:
        mock_get_recs.return_value = {
            "results": [{"id": 9, "title": "Rec", "vote_average": 7.0, "popularity": 10}]
        }
        response = client.get("/api/for-you")

    assert response.status_code == 200
    ids = [r["tmdb_id"] for r in response.json()["results"]]
    assert 9 in ids


def test_cache_hit_skips_tmdb_and_refresh_bypasses(
    client, mock_radarr, mock_sonarr, watchlist_rows
):
    """Second identical GET hits cache (no TMDB); refresh=true bypasses the cache."""
    watchlist_rows.append(types.SimpleNamespace(tmdb_id=5, media_type="movie"))
    mock_radarr.get_all_movies.return_value = []
    mock_sonarr.get_all_series.return_value = []

    with patch(
        "app.modules.clients.tmdb_client.get_recommendations",
        new_callable=AsyncMock,
    ) as mock_get_recs:
        mock_get_recs.return_value = {
            "results": [{"id": 9, "title": "Rec", "vote_average": 7.0, "popularity": 10}]
        }

        first = client.get("/api/for-you")
        assert first.status_code == 200
        after_first = mock_get_recs.call_count
        assert after_first > 0

        second = client.get("/api/for-you")
        assert second.status_code == 200
        assert mock_get_recs.call_count == after_first

        third = client.get("/api/for-you?refresh=true")
        assert third.status_code == 200
        assert mock_get_recs.call_count > after_first


def test_tmdb_all_fail_returns_empty_but_not_cached(
    client, mock_radarr, mock_sonarr, watchlist_rows
):
    """All TMDB rec calls failing -> empty result (200) that is NOT cached.

    A second request once TMDB is healthy must recompute and return real data,
    proving a transient blip does not poison the 6h cache with an empty list.
    """
    watchlist_rows.append(types.SimpleNamespace(tmdb_id=5, media_type="movie"))
    mock_radarr.get_all_movies.return_value = []
    mock_sonarr.get_all_series.return_value = []

    with patch(
        "app.modules.clients.tmdb_client.get_recommendations",
        new_callable=AsyncMock,
    ) as mock_get_recs:
        mock_get_recs.side_effect = TMDBNetworkError("tmdb down")
        first = client.get("/api/for-you")
        assert first.status_code == 200
        assert first.json()["results"] == []

        mock_get_recs.side_effect = None
        mock_get_recs.return_value = {
            "results": [{"id": 9, "title": "Rec", "vote_average": 7.0, "popularity": 10}]
        }
        second = client.get("/api/for-you")
        assert second.status_code == 200
        ids = [r["tmdb_id"] for r in second.json()["results"]]
        assert 9 in ids


def test_arr_failure_served_but_not_cached_and_warns(
    client, mock_radarr, mock_sonarr, watchlist_rows, caplog
):
    """An arr fetch raising -> recs still served (200) but result is NOT cached and a
    warning is logged; a later healthy request recomputes rather than serving a cache hit.
    """
    watchlist_rows.append(types.SimpleNamespace(tmdb_id=5, media_type="movie"))
    mock_radarr.get_all_movies.side_effect = httpx.ConnectError("boom")
    mock_sonarr.get_all_series.return_value = []

    with patch(
        "app.modules.clients.tmdb_client.get_recommendations",
        new_callable=AsyncMock,
    ) as mock_get_recs:
        mock_get_recs.return_value = {
            "results": [{"id": 9, "title": "Rec", "vote_average": 7.0, "popularity": 10}]
        }
        with caplog.at_level(logging.WARNING):
            first = client.get("/api/for-you")
        assert first.status_code == 200
        ids = [r["tmdb_id"] for r in first.json()["results"]]
        assert 9 in ids
        after_first = mock_get_recs.call_count
        assert after_first > 0
        assert any(rec.levelno == logging.WARNING for rec in caplog.records)

        mock_radarr.get_all_movies.side_effect = None
        mock_radarr.get_all_movies.return_value = []
        second = client.get("/api/for-you")
        assert second.status_code == 200
        assert mock_get_recs.call_count > after_first
