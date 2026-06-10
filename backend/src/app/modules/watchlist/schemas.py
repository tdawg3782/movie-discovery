"""Watchlist batch operation schemas."""
from typing import Literal
from pydantic import BaseModel


class BatchProcessRequest(BaseModel):
    """Request to process multiple watchlist items."""

    ids: list[int]  # TMDB IDs
    media_type: Literal["movie", "show"]


class BatchProcessResponse(BaseModel):
    """Response from batch processing."""

    processed: list[int]  # Successfully processed TMDB IDs
    failed: list[dict]  # Failed items with error messages


class BatchDeleteItem(BaseModel):
    """A single (tmdb_id, media_type) pair to delete."""

    tmdb_id: int
    media_type: Literal["movie", "show"]


class BatchDeleteRequest(BaseModel):
    """Request to delete multiple watchlist items."""

    items: list[BatchDeleteItem]
