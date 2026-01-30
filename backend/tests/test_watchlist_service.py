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
