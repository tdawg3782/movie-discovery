"""Pure normalization/merge/sort functions for the unified release calendar.

No I/O. Every normalizer emits dicts of the shared agenda-entry shape:
    {
        "date": "2026-06-10",                  # YYYY-MM-DD (date portion only)
        "kind": "episode" | "movie",
        "source": "sonarr" | "radarr" | "watchlist",
        "title": str,
        "subtitle": str | None,                # episodes only; None otherwise
        "tmdb_id": int | None,                 # None when unavailable
        "in_library": bool,                    # sonarr/radarr True; watchlist False
    }
"""
from datetime import date, timedelta


def default_window(today: date) -> tuple[str, str]:
    """Return (today, today+7) as YYYY-MM-DD strings."""
    return today.isoformat(), (today + timedelta(days=7)).isoformat()


def _date_portion(value: str | None) -> str | None:
    """Take the date portion (first 10 chars / before 'T') of an ISO timestamp."""
    if not value:
        return None
    return value.split("T", 1)[0][:10]


def normalize_sonarr(records: list[dict]) -> list[dict]:
    """Normalize Sonarr calendar episode records into agenda entries."""
    entries: list[dict] = []
    for record in records:
        entry_date = _date_portion(record.get("airDateUtc")) or _date_portion(
            record.get("airDate")
        )
        series = record.get("series") or {}
        title = series.get("title") or record.get("seriesTitle")
        sn = record.get("seasonNumber")
        en = record.get("episodeNumber")
        episode_title = record.get("title")
        if isinstance(sn, int) and isinstance(en, int):
            subtitle = f"S{sn:02d}E{en:02d}"
            if episode_title:
                subtitle += f" · {episode_title}"
        else:
            subtitle = episode_title or None
        entries.append(
            {
                "date": entry_date,
                "kind": "episode",
                "source": "sonarr",
                "title": title,
                "subtitle": subtitle,
                "tmdb_id": series.get("tmdbId"),
                "in_library": True,
            }
        )
    return entries


def normalize_radarr(records: list[dict], start: str) -> list[dict]:
    """Normalize Radarr calendar movie records into agenda entries.

    For each movie pick the soonest release date >= start among digitalRelease,
    physicalRelease, and inCinemas. Records without any in-window date are skipped.
    """
    entries: list[dict] = []
    for record in records:
        candidates = [
            _date_portion(record.get("digitalRelease")),
            _date_portion(record.get("physicalRelease")),
            _date_portion(record.get("inCinemas")),
        ]
        in_window = sorted(d for d in candidates if d and d >= start)
        if not in_window:
            continue
        entries.append(
            {
                "date": in_window[0],
                "kind": "movie",
                "source": "radarr",
                "title": record.get("title"),
                "subtitle": None,
                "tmdb_id": record.get("tmdbId"),
                "in_library": True,
            }
        )
    return entries


def normalize_watchlist_movies(
    movies: list[dict], start: str, end: str
) -> list[dict]:
    """Normalize pre-resolved watchlist movies into agenda entries.

    Each input item is {"tmdb_id", "title", "release_date"}. Keep only items with a
    truthy release_date within [start, end] (lexicographic compare on YYYY-MM-DD).
    """
    entries: list[dict] = []
    for movie in movies:
        release_date = movie.get("release_date")
        if not release_date or not (start <= release_date <= end):
            continue
        entries.append(
            {
                "date": release_date,
                "kind": "movie",
                "source": "watchlist",
                "title": movie.get("title"),
                "subtitle": None,
                "tmdb_id": movie.get("tmdb_id"),
                "in_library": False,
            }
        )
    return entries


def build_agenda(
    sonarr: list[dict],
    radarr: list[dict],
    watchlist: list[dict],
    start: str,
    end: str,
) -> list[dict]:
    """Merge already-normalized lists, drop falsy dates, sort by (date, title)."""
    merged = [entry for entry in (*sonarr, *radarr, *watchlist) if entry.get("date")]
    return sorted(merged, key=lambda entry: (entry["date"], entry.get("title") or ""))
