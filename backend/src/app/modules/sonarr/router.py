"""Sonarr API routes."""
from fastapi import APIRouter, Depends, HTTPException, Path
from httpx import HTTPStatusError, TimeoutException

from app.config import settings
from app.schemas import AddMediaRequest, AddMediaResponse, LibraryStatusResponse
from .client import SonarrClient


def get_sonarr_client() -> SonarrClient:
    """Dependency to get Sonarr client instance."""
    return SonarrClient(url=settings.sonarr_url, api_key=settings.sonarr_api_key)


router = APIRouter(prefix="/api/sonarr", tags=["sonarr"])


@router.get("/status/{tmdb_id}", response_model=LibraryStatusResponse)
async def get_series_status(
    tmdb_id: int = Path(gt=0, description="TMDB series ID"),
    client: SonarrClient = Depends(get_sonarr_client),
):
    """Check if series is in Sonarr library."""
    status = await client.get_status(tmdb_id)
    series = await client.lookup_series(tmdb_id)
    return LibraryStatusResponse(
        tmdb_id=tmdb_id,
        media_type="show",
        status=status,
        title=series.get("title") if series else None,
    )


@router.post("/add", response_model=AddMediaResponse)
async def add_series(
    data: AddMediaRequest, client: SonarrClient = Depends(get_sonarr_client)
):
    """Add series to Sonarr."""
    try:
        result = await client.add_series(
            tmdb_id=data.tmdb_id,
            quality_profile_id=data.quality_profile_id,
        )
        return AddMediaResponse(
            success=True,
            message=f"Added {result.get('title', 'series')} to Sonarr",
            tmdb_id=data.tmdb_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except TimeoutException:
        raise HTTPException(status_code=504, detail="Sonarr request timed out")
    except HTTPStatusError as e:
        raise HTTPException(
            status_code=503, detail=f"Sonarr API error: {e.response.status_code}"
        )
