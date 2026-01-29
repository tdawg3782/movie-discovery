"""Library API routes for combined Radarr/Sonarr data."""
from fastapi import APIRouter, Depends, Query

from app.config import settings
from app.modules.radarr.client import RadarrClient
from app.modules.sonarr.client import SonarrClient


def get_radarr_client() -> RadarrClient:
    """Dependency to get Radarr client instance."""
    return RadarrClient(url=settings.radarr_url, api_key=settings.radarr_api_key)


def get_sonarr_client() -> SonarrClient:
    """Dependency to get Sonarr client instance."""
    return SonarrClient(url=settings.sonarr_url, api_key=settings.sonarr_api_key)


router = APIRouter(prefix="/api/library", tags=["library"])


@router.get("/activity")
async def get_library_activity(
    limit: int = Query(20, le=100),
    radarr: RadarrClient = Depends(get_radarr_client),
    sonarr: SonarrClient = Depends(get_sonarr_client)
):
    """Get combined recent activity from Radarr and Sonarr."""
    movies = await radarr.get_recent(limit)
    shows = await sonarr.get_recent(limit)

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
    radarr_queue = await radarr.get_queue()
    sonarr_queue = await sonarr.get_queue()

    return {
        "movies": radarr_queue.get("records", []),
        "shows": sonarr_queue.get("records", [])
    }
