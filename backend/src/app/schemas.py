"""Pydantic schemas for API request/response models."""
from datetime import datetime
from pydantic import BaseModel


# === Media Schemas ===

class MediaBase(BaseModel):
    """Base media information."""

    tmdb_id: int
    media_type: str  # 'movie' or 'show'
    title: str
    overview: str | None = None
    poster_path: str | None = None
    release_date: str | None = None
    vote_average: float | None = None


class MediaResponse(MediaBase):
    """Media item in API responses."""

    library_status: str | None = None  # 'available', 'downloading', 'added', None


class MediaList(BaseModel):
    """List of media items."""

    results: list[MediaResponse]
    page: int = 1
    total_pages: int = 1
    total_results: int = 0


# === Watchlist Schemas ===

class WatchlistAdd(BaseModel):
    """Request to add item to watchlist."""

    tmdb_id: int
    media_type: str
    notes: str | None = None


class WatchlistItem(MediaBase):
    """Watchlist item response."""

    id: int
    added_at: datetime
    notes: str | None = None
    status: str = "pending"  # pending, added, downloading


class WatchlistResponse(BaseModel):
    """Watchlist list response."""

    items: list[WatchlistItem]
    total: int


# === Sonarr/Radarr Schemas ===

class AddMediaRequest(BaseModel):
    """Request to add media to Sonarr/Radarr."""

    tmdb_id: int
    quality_profile_id: int | None = None


class LibraryStatusResponse(BaseModel):
    """Status of media in Sonarr/Radarr."""

    tmdb_id: int
    media_type: str
    status: str  # 'available', 'downloading', 'added', 'not_found'
    title: str | None = None


class AddMediaResponse(BaseModel):
    """Response after adding media."""

    success: bool
    message: str
    tmdb_id: int


class BatchStatusRequest(BaseModel):
    """Request for batch status check."""

    tmdb_ids: list[int]


class BatchStatusResponse(BaseModel):
    """Response with statuses for multiple items."""

    statuses: dict[int, str | None]  # tmdb_id -> status or None if not in library
