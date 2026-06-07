"""Tests for watchlist service."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.modules.watchlist.service import WatchlistService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def service(db_session):
    return WatchlistService(db_session)


def test_add_to_watchlist(service):
    item = service.add(tmdb_id=123, media_type="movie", notes="Test note")
    assert item.tmdb_id == 123
    assert item.media_type == "movie"
    assert item.notes == "Test note"


def test_get_watchlist(service):
    service.add(tmdb_id=123, media_type="movie")
    service.add(tmdb_id=456, media_type="show")

    items = service.get_all()
    assert len(items) == 2


def test_remove_from_watchlist(service):
    item = service.add(tmdb_id=123, media_type="movie")
    service.remove(item.id)

    items = service.get_all()
    assert len(items) == 0


def test_duplicate_add_returns_existing(service):
    item1 = service.add(tmdb_id=123, media_type="movie")
    item2 = service.add(tmdb_id=123, media_type="movie")
    assert item1.id == item2.id


def test_add_with_selected_seasons(service):
    """Service stores selected_seasons as JSON."""
    item = service.add(tmdb_id=12345, media_type="show", selected_seasons=[1, 2, 3])
    assert item.selected_seasons == "[1, 2, 3]"


def test_add_without_seasons_stores_null(service):
    """Service stores None when no seasons specified."""
    item = service.add(tmdb_id=12345, media_type="show")
    assert item.selected_seasons is None


def test_update_details_priority_only(service):
    """Setting only priority leaves notes/tags untouched."""
    item = service.add(tmdb_id=111, media_type="movie", notes="keep me")
    updated = service.update_details(item.id, {"priority": 1})
    assert updated.priority == 1
    assert updated.notes == "keep me"
    assert updated.tags is None


def test_update_details_notes(service):
    """Setting notes updates only notes."""
    item = service.add(tmdb_id=222, media_type="movie")
    updated = service.update_details(item.id, {"notes": "soon"})
    assert updated.notes == "soon"


def test_update_details_tags_stored_as_json(service):
    """Populated tags stored as JSON string."""
    item = service.add(tmdb_id=333, media_type="movie")
    updated = service.update_details(item.id, {"tags": ["a", "b"]})
    assert updated.tags == '["a", "b"]'


def test_update_details_empty_tags_stored_null(service):
    """Empty tags list stored as None."""
    item = service.add(tmdb_id=444, media_type="movie")
    updated = service.update_details(item.id, {"tags": []})
    assert updated.tags is None


def test_update_details_unknown_id_returns_none(service):
    """Unknown item_id returns None."""
    assert service.update_details(99999, {"priority": 1}) is None
