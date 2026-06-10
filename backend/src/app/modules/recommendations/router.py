"""For You recommendations endpoint: aggregate TMDB recommendations from local seeds."""
import asyncio
import logging
import time

from fastapi import APIRouter, Depends, Query

from app.schemas import MediaList, MediaResponse
from app.modules.discovery.tmdb_client import TMDBClient
from app.modules.radarr.router import get_radarr_client
from app.modules.sonarr.router import get_sonarr_client
from app.modules.radarr.client import RadarrClient
from app.modules.sonarr.client import SonarrClient
from app.modules.watchlist.router import get_service
from app.modules.watchlist.service import WatchlistService
from app.modules.clients import get_tmdb_client
from . import service

router = APIRouter(prefix="/api/for-you", tags=["recommendations"])

logger = logging.getLogger(__name__)

RECS_CACHE_TTL = 6 * 3600
_cache: dict = {}


def reset_cache() -> None:
    """Clear the in-process recommendations cache (test isolation)."""
    _cache.clear()


@router.get("", response_model=MediaList)
async def get_for_you(
    refresh: bool = Query(False),
    radarr: RadarrClient = Depends(get_radarr_client),
    sonarr: SonarrClient = Depends(get_sonarr_client),
    wl: WatchlistService = Depends(get_service),
    tmdb: TMDBClient = Depends(get_tmdb_client),
):
    """Recommend titles the user does not already own/watchlist, seeded from local data."""
    watchlist_keys = [(i.media_type, i.tmdb_id) for i in wl.get_all()]

    owned_keys: list[tuple[str, int]] = []
    degraded = False
    try:
        for m in await radarr.get_all_movies():
            tid = m.get("tmdbId")
            if tid:
                owned_keys.append(("movie", tid))
    except Exception:
        degraded = True
        logger.warning("Radarr library fetch failed; serving degraded recommendations")
    try:
        for s in await sonarr.get_all_series():
            tid = s.get("tmdbId")
            if tid:
                owned_keys.append(("show", tid))
    except Exception:
        degraded = True
        logger.warning("Sonarr library fetch failed; serving degraded recommendations")

    seeds = service.select_seeds(watchlist_keys, owned_keys)
    exclude = service.exclusion_set(watchlist_keys, owned_keys)

    if not seeds:
        return MediaList(results=[], page=1, total_pages=1, total_results=0)

    sig = frozenset(seeds)
    if not refresh and _cache.get("sig") == sig and (time.monotonic() - _cache.get("at", 0)) < RECS_CACHE_TTL:
        return _cache["value"]

    coros = [
        tmdb.get_recommendations(tid, "tv" if mt == "show" else "movie")
        for (mt, tid) in seeds
    ]
    results = await asyncio.gather(*coros, return_exceptions=True)
    rec_results: list[tuple[str, list[dict]]] = []
    for (mt, _tid), data in zip(seeds, results):
        if isinstance(data, Exception):
            degraded = True
            continue
        rec_results.append((mt, data.get("results", [])))

    ranked = service.aggregate(rec_results, exclude)
    media_list = MediaList(
        results=[MediaResponse(**r) for r in ranked],
        page=1,
        total_pages=1,
        total_results=len(ranked),
    )
    if rec_results and not degraded:
        _cache["sig"] = sig
        _cache["value"] = media_list
        _cache["at"] = time.monotonic()
    return media_list
