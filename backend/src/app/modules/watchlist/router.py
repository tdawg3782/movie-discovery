"""Watchlist API routes."""
import asyncio
import json
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import WatchlistAdd, WatchlistItem, WatchlistResponse
from app.modules.discovery.tmdb_client import TMDBClient, TMDBClientError, TMDBAPIError
from app.modules.clients import get_tmdb_client
from .service import WatchlistService
from .schemas import BatchProcessRequest, BatchProcessResponse, BatchDeleteRequest


class UpdateSeasonsRequest(BaseModel):
    selected_seasons: list[int] | None


class UpdateDetailsRequest(BaseModel):
    priority: Literal[-1, 0, 1] | None = None
    notes: str | None = None
    tags: list[str] | None = None

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


def get_service(db: Session = Depends(get_db)) -> WatchlistService:
    return WatchlistService(db)


def _parse_seasons(raw: str | None) -> list[int] | None:
    """Parse JSON-encoded seasons string, returning None on failure."""
    if not raw:
        return None
    try:
        result = json.loads(raw)
        return result if isinstance(result, list) else None
    except json.JSONDecodeError:
        return None


def _parse_tags(raw: str | None) -> list[str]:
    """Parse JSON-encoded tags string, returning [] on null/garbage."""
    if not raw:
        return []
    try:
        result = json.loads(raw)
        return result if isinstance(result, list) else []
    except json.JSONDecodeError:
        return []


async def _enrich_watchlist_item(item, tmdb: TMDBClient) -> WatchlistItem:
    """Enrich a watchlist DB row with TMDB metadata."""
    selected_seasons = _parse_seasons(item.selected_seasons)

    try:
        tmdb_type = "tv" if item.media_type == "show" else item.media_type
        details = await tmdb.get_details(item.tmdb_id, tmdb_type)

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
            priority=item.priority,
            tags=_parse_tags(item.tags),
        )
    except TMDBAPIError as e:
        if e.status_code != 404:
            raise
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
            priority=item.priority,
            tags=_parse_tags(item.tags),
        )


@router.get("", response_model=WatchlistResponse)
async def get_watchlist(service: WatchlistService = Depends(get_service)):
    """Get all watchlist items with enriched metadata from TMDB."""
    items = service.get_all()

    if not items:
        return WatchlistResponse(items=[], total=0)

    tmdb = get_tmdb_client()
    try:
        enriched_items = await asyncio.gather(*[_enrich_watchlist_item(item, tmdb) for item in items])
    except TMDBClientError:
        raise HTTPException(status_code=502, detail="TMDB unavailable")

    return WatchlistResponse(items=list(enriched_items), total=len(enriched_items))


@router.post("", response_model=WatchlistItem, status_code=201)
async def add_to_watchlist(
    data: WatchlistAdd, response: Response, service: WatchlistService = Depends(get_service)
):
    """Add item to watchlist."""
    item, created = service.add(
        tmdb_id=data.tmdb_id,
        media_type=data.media_type,
        notes=data.notes,
        selected_seasons=data.selected_seasons,
        is_season_update=data.is_season_update
    )
    if not created:
        response.status_code = 200

    tmdb = get_tmdb_client()
    try:
        return await _enrich_watchlist_item(item, tmdb)
    except TMDBClientError:
        raise HTTPException(status_code=502, detail="TMDB unavailable")


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
    """Delete multiple watchlist items by (TMDB id, media type)."""
    items = [(i.tmdb_id, i.media_type) for i in request.items]
    count = service.delete_batch(items)
    return {"deleted": count}


@router.patch("/{tmdb_id}/seasons")
async def update_watchlist_seasons(
    tmdb_id: int,
    data: UpdateSeasonsRequest,
    service: WatchlistService = Depends(get_service)
):
    """Update selected seasons for a watchlist item."""
    item = service.update_seasons(tmdb_id, "show", data.selected_seasons)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    return {"success": True, "selected_seasons": _parse_seasons(item.selected_seasons)}


@router.patch("/{item_id}/details")
async def update_watchlist_details(item_id: int, data: UpdateDetailsRequest,
                                   service: WatchlistService = Depends(get_service)):
    fields = data.model_dump(exclude_unset=True)
    item = service.update_details(item_id, fields)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    tmdb = get_tmdb_client()
    try:
        return await _enrich_watchlist_item(item, tmdb)
    except TMDBClientError:
        raise HTTPException(status_code=502, detail="TMDB unavailable")


# Parameterized endpoint must come AFTER specific endpoints
@router.delete("/{item_id}")
async def remove_from_watchlist(
    item_id: int, service: WatchlistService = Depends(get_service)
):
    """Remove item from watchlist."""
    if not service.remove(item_id):
        raise HTTPException(status_code=404, detail="Item not found")
    return {"success": True}
