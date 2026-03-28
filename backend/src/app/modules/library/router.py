"""Library API routes for combined Radarr/Sonarr data."""
import asyncio
from fastapi import APIRouter, Depends, Query

from app.modules.radarr.router import get_radarr_client
from app.modules.sonarr.router import get_sonarr_client
from app.modules.radarr.client import RadarrClient
from app.modules.sonarr.client import SonarrClient


router = APIRouter(prefix="/api/library", tags=["library"])


@router.get("/activity")
async def get_library_activity(
    limit: int = Query(20, le=100),
    radarr: RadarrClient = Depends(get_radarr_client),
    sonarr: SonarrClient = Depends(get_sonarr_client)
):
    """Get combined recent activity from Radarr and Sonarr."""
    # Run both calls in parallel for faster response
    movies, shows = await asyncio.gather(
        radarr.get_recent(limit),
        sonarr.get_recent(limit),
    )

    return {
        "movies": movies,
        "shows": shows
    }


@router.get("/queue")
async def get_combined_queue(
    radarr: RadarrClient = Depends(get_radarr_client),
    sonarr: SonarrClient = Depends(get_sonarr_client)
):
    """Get combined download queue from Radarr and Sonarr."""
    # Run both calls in parallel for faster response
    radarr_queue, sonarr_queue = await asyncio.gather(
        radarr.get_queue(),
        sonarr.get_queue(),
    )

    return {
        "movies": radarr_queue.get("records", []),
        "shows": sonarr_queue.get("records", [])
    }
