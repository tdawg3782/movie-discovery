"""Tests for the calendar aggregating endpoint."""
import types

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app
from app.modules.radarr.router import get_radarr_client
from app.modules.sonarr.router import get_sonarr_client
from app.modules.watchlist.router import get_service
from app.modules.radarr.client import RadarrClient
from app.modules.sonarr.client import SonarrClient


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
    app.dependency_overrides[get_radarr_client] = lambda: mock_radarr
    app.dependency_overrides[get_sonarr_client] = lambda: mock_sonarr
    app.dependency_overrides[get_service] = lambda: FakeWatchlistService(watchlist_rows)
    yield TestClient(app)
    app.dependency_overrides.clear()


WINDOW = "?start=2026-06-06&end=2026-06-13"


def test_empty_everything_returns_empty_items(client, mock_radarr, mock_sonarr):
    """All sources empty -> {"items": []}."""
    mock_radarr.get_calendar.return_value = []
    mock_sonarr.get_calendar.return_value = []

    response = client.get(f"/api/calendar{WINDOW}")

    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_sonarr_and_radarr_records_sorted(client, mock_radarr, mock_sonarr):
    """One sonarr episode + one radarr movie -> two sorted, correctly-typed items."""
    mock_sonarr.get_calendar.return_value = [
        {
            "airDateUtc": "2026-06-12T01:00:00Z",
            "series": {"title": "My Show", "tmdbId": 42},
            "seasonNumber": 2,
            "episodeNumber": 5,
            "title": "Pilot",
        }
    ]
    mock_radarr.get_calendar.return_value = [
        {
            "title": "My Movie",
            "tmdbId": 7,
            "digitalRelease": "2026-06-10T00:00:00Z",
        }
    ]

    response = client.get(f"/api/calendar{WINDOW}")

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 2
    # Sorted ascending by date: movie (06-10) before episode (06-12).
    assert [i["date"] for i in items] == sorted(i["date"] for i in items)
    assert items[0]["source"] == "radarr"
    assert items[0]["kind"] == "movie"
    assert items[0]["date"] == "2026-06-10"
    assert items[1]["source"] == "sonarr"
    assert items[1]["kind"] == "episode"
    assert items[1]["date"] == "2026-06-12"
    for i in items:
        assert "2026-06-06" <= i["date"] <= "2026-06-13"


def test_watchlist_movie_resolved_via_tmdb(client, mock_radarr, mock_sonarr, watchlist_rows):
    """A pending watchlist movie is resolved through TMDB into a watchlist agenda entry."""
    mock_radarr.get_calendar.return_value = []
    mock_sonarr.get_calendar.return_value = []
    watchlist_rows.append(
        types.SimpleNamespace(tmdb_id=99, media_type="movie", status="pending")
    )

    with patch(
        "app.modules.calendar.router.tmdb_client.get_details",
        new_callable=AsyncMock,
        return_value={"title": "Future Film", "release_date": "2026-06-10"},
    ):
        response = client.get(f"/api/calendar{WINDOW}")

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    entry = items[0]
    assert entry["source"] == "watchlist"
    assert entry["in_library"] is False
    assert entry["title"] == "Future Film"
    assert entry["tmdb_id"] == 99
    assert entry["date"] == "2026-06-10"
