"""Watchlist API routes."""
import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import WatchlistAdd, WatchlistItem, WatchlistResponse
from app.config import settings
from app.modules.discovery.tmdb_client import TMDBClient
from .service import WatchlistService
from .schemas import BatchProcessRequest, BatchProcessResponse, BatchDeleteRequest

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


def get_service(db: Session = Depends(get_db)) -> WatchlistService:
    return WatchlistService(db)


@router.get("", response_model=WatchlistResponse)
async def get_watchlist(service: WatchlistService = Depends(get_service)):
    """Get all watchlist items with enriched metadata from TMDB."""
    items = service.get_all()

    if not items:
        return WatchlistResponse(items=[], total=0)

    # Fetch metadata from TMDB concurrently
    tmdb = TMDBClient(api_key=settings.tmdb_api_key)

    async def enrich_item(item):
        try:
            # Convert 'show' to 'tv' for TMDB API
            tmdb_type = "tv" if item.media_type == "show" else item.media_type
            details = await tmdb.get_details(item.tmdb_id, tmdb_type)

            # Parse selected_seasons from JSON
            selected_seasons = None
            if item.selected_seasons:
                selected_seasons = json.loads(item.selected_seasons)

            # Get total seasons from TMDB (only for shows)
            total_seasons = None
            if item.media_type == "show":
                total_seasons = details.get("number_of_seasons")

            return WatchlistItem(
                id=item.id,
                tmdb_id=item.tmdb_id,
                media_type=item.media_type,
                title=details.get("title") or details.get("name") or f"TMDB:{item.tmdb_id}",
                overview=details.get("overview"),
                poster_path=details.get("poster_path"),
                release_date=details.get("release_date") or details.get("first_air_date"),
                vote_average=details.get("vote_average"),
                added_at=item.added_at,
                notes=item.notes,
                status=item.status,
                selected_seasons=selected_seasons,
                total_seasons=total_seasons,
            )
        except Exception:
            # Fallback if TMDB fails - still parse selected_seasons
            selected_seasons = None
            if item.selected_seasons:
                try:
                    selected_seasons = json.loads(item.selected_seasons)
                except json.JSONDecodeError:
                    pass

            return WatchlistItem(
                id=item.id,
                tmdb_id=item.tmdb_id,
                media_type=item.media_type,
                title=f"TMDB:{item.tmdb_id}",
                added_at=item.added_at,
                notes=item.notes,
                status=item.status,
                selected_seasons=selected_seasons,
                total_seasons=None,
            )

    enriched_items = await asyncio.gather(*[enrich_item(item) for item in items])

    return WatchlistResponse(items=list(enriched_items), total=len(enriched_items))


@router.post("", response_model=WatchlistItem, status_code=201)
async def add_to_watchlist(
    data: WatchlistAdd, service: WatchlistService = Depends(get_service)
):
    """Add item to watchlist."""
    item = service.add(
        tmdb_id=data.tmdb_id,
        media_type=data.media_type,
        notes=data.notes,
        selected_seasons=data.selected_seasons
    )

    # Fetch metadata from TMDB
    tmdb = TMDBClient(api_key=settings.tmdb_api_key)
    try:
        tmdb_type = "tv" if item.media_type == "show" else item.media_type
        details = await tmdb.get_details(item.tmdb_id, tmdb_type)

        # Parse selected_seasons from JSON
        selected_seasons = None
        if item.selected_seasons:
            selected_seasons = json.loads(item.selected_seasons)

        # Get total seasons from TMDB (only for shows)
        total_seasons = None
        if item.media_type == "show":
            total_seasons = details.get("number_of_seasons")

        return WatchlistItem(
            id=item.id,
            tmdb_id=item.tmdb_id,
            media_type=item.media_type,
            title=details.get("title") or details.get("name") or f"TMDB:{item.tmdb_id}",
            overview=details.get("overview"),
            poster_path=details.get("poster_path"),
            release_date=details.get("release_date") or details.get("first_air_date"),
            vote_average=details.get("vote_average"),
            added_at=item.added_at,
            notes=item.notes,
            status=item.status,
            selected_seasons=selected_seasons,
            total_seasons=total_seasons,
        )
    except Exception:
        # Fallback if TMDB fails - still parse selected_seasons
        selected_seasons = None
        if item.selected_seasons:
            try:
                selected_seasons = json.loads(item.selected_seasons)
            except json.JSONDecodeError:
                pass

        return WatchlistItem(
            id=item.id,
            tmdb_id=item.tmdb_id,
            media_type=item.media_type,
            title=f"TMDB:{item.tmdb_id}",
            added_at=item.added_at,
            notes=item.notes,
            status=item.status,
            selected_seasons=selected_seasons,
            total_seasons=None,
        )


# Batch endpoints must come BEFORE parameterized endpoints
@router.post("/process", response_model=BatchProcessResponse)
async def process_watchlist_items(
    request: BatchProcessRequest, service: WatchlistService = Depends(get_service)
):
    """Process watchlist items by sending to Radarr/Sonarr."""
    processed, failed = await service.process_batch(request.ids, request.media_type)
    return BatchProcessResponse(processed=processed, failed=failed)


@router.delete("/batch")
async def delete_watchlist_items(
    request: BatchDeleteRequest, service: WatchlistService = Depends(get_service)
):
    """Delete multiple watchlist items by TMDB ID."""
    count = service.delete_batch(request.ids)
    return {"deleted": count}


# Parameterized endpoint must come AFTER specific endpoints
@router.delete("/{item_id}")
async def remove_from_watchlist(
    item_id: int, service: WatchlistService = Depends(get_service)
):
    """Remove item from watchlist."""
    if not service.remove(item_id):
        raise HTTPException(status_code=404, detail="Item not found")
    return {"success": True}
