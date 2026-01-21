"""Radarr API routes."""
from fastapi import APIRouter, Depends, HTTPException, Path
from httpx import HTTPStatusError, TimeoutException

from app.config import settings
from app.schemas import AddMediaRequest, AddMediaResponse, LibraryStatusResponse
from .client import RadarrClient


def get_radarr_client() -> RadarrClient:
    """Dependency to get Radarr client instance."""
    return RadarrClient(url=settings.radarr_url, api_key=settings.radarr_api_key)


router = APIRouter(prefix="/api/radarr", tags=["radarr"])


@router.get("/status/{tmdb_id}", response_model=LibraryStatusResponse)
async def get_movie_status(
    tmdb_id: int = Path(gt=0, description="TMDB movie ID"),
    client: RadarrClient = Depends(get_radarr_client),
):
    """Check if movie is in Radarr library."""
    status = await client.get_status(tmdb_id)
    movie = await client.lookup_movie(tmdb_id)
    return LibraryStatusResponse(
        tmdb_id=tmdb_id,
        media_type="movie",
        status=status,
        title=movie.get("title") if movie else None,
    )


@router.post("/add", response_model=AddMediaResponse)
async def add_movie(
    data: AddMediaRequest, client: RadarrClient = Depends(get_radarr_client)
):
    """Add movie to Radarr."""
    try:
        result = await client.add_movie(
            tmdb_id=data.tmdb_id,
            quality_profile_id=data.quality_profile_id or 1,
        )
        return AddMediaResponse(
            success=True,
            message=f"Added {result.get('title', 'movie')} to Radarr",
            tmdb_id=data.tmdb_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except TimeoutException:
        raise HTTPException(status_code=504, detail="Radarr request timed out")
    except HTTPStatusError as e:
        raise HTTPException(
            status_code=503, detail=f"Radarr API error: {e.response.status_code}"
        )
