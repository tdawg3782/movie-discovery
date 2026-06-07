"""Unit tests for the pure calendar service functions (no mocks)."""
from datetime import date

from app.modules.calendar import service


def test_default_window():
    """default_window returns today and today+7 as ISO date strings."""
    assert service.default_window(date(2026, 6, 6)) == ("2026-06-06", "2026-06-13")


def test_normalize_sonarr_builds_episode_entry():
    """A sonarr record becomes a single episode agenda entry."""
    records = [
        {
            "airDateUtc": "2026-06-10T01:00:00Z",
            "series": {"title": "My Show", "tmdbId": 42},
            "seasonNumber": 2,
            "episodeNumber": 5,
            "title": "Pilot",
        }
    ]

    entries = service.normalize_sonarr(records)

    assert len(entries) == 1
    entry = entries[0]
    assert entry["date"] == "2026-06-10"
    assert entry["subtitle"] == "S02E05 · Pilot"
    assert entry["title"] == "My Show"
    assert entry["kind"] == "episode"
    assert entry["source"] == "sonarr"
    assert entry["in_library"] is True
    assert entry["tmdb_id"] == 42


def test_normalize_radarr_picks_soonest_in_window_and_skips_past():
    """Radarr normalizer picks soonest date >= start; skips records with no in-window date."""
    records = [
        {
            "title": "In Window Movie",
            "tmdbId": 7,
            "inCinemas": "2026-05-01T00:00:00Z",
            "digitalRelease": "2026-06-10T00:00:00Z",
        },
        {
            "title": "Past Movie",
            "tmdbId": 8,
            "inCinemas": "2026-05-30T00:00:00Z",
        },
    ]

    entries = service.normalize_radarr(records, start="2026-06-06")

    assert len(entries) == 1
    entry = entries[0]
    assert entry["title"] == "In Window Movie"
    assert entry["date"] == "2026-06-10"
    assert entry["kind"] == "movie"
    assert entry["source"] == "radarr"
    assert entry["in_library"] is True
    assert entry["subtitle"] is None
    assert entry["tmdb_id"] == 7
    assert all(e["title"] != "Past Movie" for e in entries)


def test_normalize_watchlist_movies_filters_to_window():
    """Watchlist normalizer keeps in-window release dates and drops out-of-window ones."""
    movies = [
        {"tmdb_id": 1, "title": "A", "release_date": "2026-06-10"},
        {"tmdb_id": 2, "title": "B", "release_date": "2026-07-01"},
    ]

    entries = service.normalize_watchlist_movies(
        movies, start="2026-06-06", end="2026-06-13"
    )

    assert len(entries) == 1
    entry = entries[0]
    assert entry["title"] == "A"
    assert entry["date"] == "2026-06-10"
    assert entry["kind"] == "movie"
    assert entry["source"] == "watchlist"
    assert entry["in_library"] is False
    assert entry["subtitle"] is None
    assert entry["tmdb_id"] == 1


def test_build_agenda_merges_sorts_and_drops_falsy_dates():
    """build_agenda concatenates normalized lists, drops falsy dates, sorts by (date, title)."""
    sonarr = [
        {"date": "2026-06-12", "title": "Zeta", "kind": "episode", "source": "sonarr"},
        {"date": "", "title": "NoDate", "kind": "episode", "source": "sonarr"},
    ]
    radarr = [
        {"date": "2026-06-10", "title": "Beta", "kind": "movie", "source": "radarr"},
    ]
    watchlist = [
        {"date": "2026-06-10", "title": "Alpha", "kind": "movie", "source": "watchlist"},
    ]

    agenda = service.build_agenda(
        sonarr, radarr, watchlist, start="2026-06-06", end="2026-06-13"
    )

    assert [e["title"] for e in agenda] == ["Alpha", "Beta", "Zeta"]
    assert all(e["date"] for e in agenda)
