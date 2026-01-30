"""Tests for watchlist schemas with season selection."""
import pytest
from app.schemas import WatchlistAdd, WatchlistItem
from datetime import datetime


def test_watchlist_add_with_seasons():
    """WatchlistAdd accepts selected_seasons."""
    data = WatchlistAdd(
        tmdb_id=12345,
        media_type="show",
        selected_seasons=[1, 2, 3]
    )
    assert data.selected_seasons == [1, 2, 3]


def test_watchlist_add_without_seasons():
    """WatchlistAdd works without selected_seasons (defaults to None)."""
    data = WatchlistAdd(tmdb_id=12345, media_type="show")
    assert data.selected_seasons is None


def test_watchlist_item_with_seasons():
    """WatchlistItem includes selected_seasons and total_seasons."""
    item = WatchlistItem(
        id=1,
        tmdb_id=12345,
        media_type="show",
        title="Test Show",
        added_at=datetime.now(),
        selected_seasons=[1, 2],
        total_seasons=5
    )
    assert item.selected_seasons == [1, 2]
    assert item.total_seasons == 5
