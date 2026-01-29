"""Watchlist API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import WatchlistAdd, WatchlistItem, WatchlistResponse
from .service import WatchlistService
from .schemas import BatchProcessRequest, BatchProcessResponse, BatchDeleteRequest

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


def get_service(db: Session = Depends(get_db)) -> WatchlistService:
    return WatchlistService(db)


@router.get("", response_model=WatchlistResponse)
async def get_watchlist(service: WatchlistService = Depends(get_service)):
    """Get all watchlist items."""
    items = service.get_all()
    return WatchlistResponse(
        items=[
            WatchlistItem(
                id=item.id,
                tmdb_id=item.tmdb_id,
                media_type=item.media_type,
                title=f"TMDB:{item.tmdb_id}",  # Would be enriched with cache
                added_at=item.added_at,
                notes=item.notes,
                status=item.status,
            )
            for item in items
        ],
        total=len(items),
    )


@router.post("", response_model=WatchlistItem, status_code=201)
async def add_to_watchlist(
    data: WatchlistAdd, service: WatchlistService = Depends(get_service)
):
    """Add item to watchlist."""
    item = service.add(
        tmdb_id=data.tmdb_id, media_type=data.media_type, notes=data.notes
    )
    return WatchlistItem(
        id=item.id,
        tmdb_id=item.tmdb_id,
        media_type=item.media_type,
        title=f"TMDB:{item.tmdb_id}",
        added_at=item.added_at,
        notes=item.notes,
        status=item.status,
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
