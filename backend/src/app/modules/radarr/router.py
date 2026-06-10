"""Radarr API routes."""
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from httpx import HTTPStatusError, TimeoutException

from app.modules.clients import get_radarr_client
from app.schemas import AddMediaRequest, AddMediaResponse, LibraryStatusResponse, BatchStatusRequest, BatchStatusResponse
from .client import RadarrClient


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
            quality_profile_id=data.quality_profile_id,
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


@router.post("/status/batch", response_model=BatchStatusResponse)
async def get_batch_status(
    data: BatchStatusRequest, client: RadarrClient = Depends(get_radarr_client)
):
    """Get library status for multiple movies at once."""
    try:
        statuses = await client.get_batch_status(data.tmdb_ids)
        return BatchStatusResponse(statuses=statuses)
    except TimeoutException:
        raise HTTPException(status_code=504, detail="Radarr request timed out")
    except HTTPStatusError as e:
        raise HTTPException(
            status_code=503, detail=f"Radarr API error: {e.response.status_code}"
        )


@router.get("/quality-profiles")
async def get_radarr_quality_profiles(client: RadarrClient = Depends(get_radarr_client)):
    """List available Radarr quality profiles for settings dropdown."""
    try:
        profiles = await client.get_quality_profiles()
        return [{"id": p["id"], "name": p["name"]} for p in profiles]
    except TimeoutException:
        raise HTTPException(status_code=504, detail="Radarr request timed out")
    except HTTPStatusError as e:
        raise HTTPException(
            status_code=503, detail=f"Radarr API error: {e.response.status_code}"
        )


@router.get("/queue")
async def get_radarr_queue(client: RadarrClient = Depends(get_radarr_client)):
    """Get current download queue from Radarr."""
    return await client.get_queue()


@router.get("/recent")
async def get_radarr_recent(
    limit: int = Query(20, le=100),
    client: RadarrClient = Depends(get_radarr_client)
):
    """Get recently added movies from Radarr."""
    return await client.get_recent(limit)
