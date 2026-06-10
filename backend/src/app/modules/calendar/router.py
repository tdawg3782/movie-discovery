"""Calendar API route aggregating upcoming releases into a unified agenda."""
import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

from app.modules.discovery.tmdb_client import TMDBClient
from app.modules.radarr.router import get_radarr_client
from app.modules.sonarr.router import get_sonarr_client
from app.modules.radarr.client import RadarrClient
from app.modules.sonarr.client import SonarrClient
from app.modules.watchlist.router import get_service
from app.modules.watchlist.service import WatchlistService
from app.modules.clients import get_tmdb_client
from . import service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


@router.get("")
async def get_calendar(
    start: str | None = Query(None),
    end: str | None = Query(None),
    radarr: RadarrClient = Depends(get_radarr_client),
    sonarr: SonarrClient = Depends(get_sonarr_client),
    wl: WatchlistService = Depends(get_service),
    tmdb: TMDBClient = Depends(get_tmdb_client),
):
    """Aggregate Sonarr/Radarr calendars and pending watchlist movies into an agenda."""
    if not start or not end:
        start, end = service.default_window(datetime.now(timezone.utc).date())

    radarr_records, sonarr_records = await asyncio.gather(
        radarr.get_calendar(start, end),
        sonarr.get_calendar(start, end),
        return_exceptions=True,
    )

    degraded: list[str] = []
    if isinstance(radarr_records, Exception):
        logger.warning("Radarr calendar unavailable; serving partial calendar")
        radarr_records = []
        degraded.append("radarr")
    if isinstance(sonarr_records, Exception):
        logger.warning("Sonarr calendar unavailable; serving partial calendar")
        sonarr_records = []
        degraded.append("sonarr")

    # Resolve watchlist movies not yet available via TMDB.
    watchlist_movies = []
    for item in wl.get_all():
        if item.media_type == "movie" and item.status not in ("added", "downloading"):
            try:
                details = await tmdb.get_details(item.tmdb_id, "movie")
                watchlist_movies.append(
                    {
                        "tmdb_id": item.tmdb_id,
                        "title": details.get("title") or f"TMDB:{item.tmdb_id}",
                        "release_date": details.get("release_date"),
                    }
                )
            except Exception:
                continue

    items = service.build_agenda(
        service.normalize_sonarr(sonarr_records),
        service.normalize_radarr(radarr_records, start),
        service.normalize_watchlist_movies(watchlist_movies, start, end),
        start,
        end,
    )
    return {"items": items, "degraded": degraded}
