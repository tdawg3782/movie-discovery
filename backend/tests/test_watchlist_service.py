"""Tests for watchlist service."""
import json
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
    item, _ = service.add(tmdb_id=123, media_type="movie", notes="Test note")
    assert item.tmdb_id == 123
    assert item.media_type == "movie"
    assert item.notes == "Test note"


def test_get_watchlist(service):
    service.add(tmdb_id=123, media_type="movie")
    service.add(tmdb_id=456, media_type="show")

    items = service.get_all()
    assert len(items) == 2


def test_remove_from_watchlist(service):
    item, _ = service.add(tmdb_id=123, media_type="movie")
    service.remove(item.id)

    items = service.get_all()
    assert len(items) == 0


def test_duplicate_add_returns_existing(service):
    item1, _ = service.add(tmdb_id=123, media_type="movie")
    item2, _ = service.add(tmdb_id=123, media_type="movie")
    assert item1.id == item2.id


def test_add_with_selected_seasons(service):
    """Service stores selected_seasons as JSON."""
    item, _ = service.add(tmdb_id=12345, media_type="show", selected_seasons=[1, 2, 3])
    assert item.selected_seasons == "[1, 2, 3]"


def test_add_without_seasons_stores_null(service):
    """Service stores None when no seasons specified."""
    item, _ = service.add(tmdb_id=12345, media_type="show")
    assert item.selected_seasons is None


def test_update_details_priority_only(service):
    """Setting only priority leaves notes/tags untouched."""
    item, _ = service.add(tmdb_id=111, media_type="movie", notes="keep me")
    updated = service.update_details(item.id, {"priority": 1})
    assert updated.priority == 1
    assert updated.notes == "keep me"
    assert updated.tags is None


def test_update_details_notes(service):
    """Setting notes updates only notes."""
    item, _ = service.add(tmdb_id=222, media_type="movie")
    updated = service.update_details(item.id, {"notes": "soon"})
    assert updated.notes == "soon"


def test_update_details_tags_stored_as_json(service):
    """Populated tags stored as JSON string."""
    item, _ = service.add(tmdb_id=333, media_type="movie")
    updated = service.update_details(item.id, {"tags": ["a", "b"]})
    assert updated.tags == '["a", "b"]'


def test_update_details_empty_tags_stored_null(service):
    """Empty tags list stored as None."""
    item, _ = service.add(tmdb_id=444, media_type="movie")
    updated = service.update_details(item.id, {"tags": []})
    assert updated.tags is None


def test_update_details_unknown_id_returns_none(service):
    """Unknown item_id returns None."""
    assert service.update_details(99999, {"priority": 1}) is None


def test_update_seasons_scoped_by_media_type(service):
    """update_seasons targets the matching media_type, leaving the sibling row untouched."""
    service.add(tmdb_id=603, media_type="movie")
    service.add(tmdb_id=603, media_type="show")

    updated = service.update_seasons(603, "show", [2])
    assert updated.media_type == "show"
    assert updated.selected_seasons == "[2]"

    # Movie sibling with the same tmdb_id is untouched
    movie_row = service.get_by_tmdb_id(603, "movie")
    assert movie_row.selected_seasons is None


def test_add_returns_created_flag(service):
    """First add returns (item, True)."""
    item, created = service.add(tmdb_id=700, media_type="show")
    assert created is True
    assert item.tmdb_id == 700


def test_readd_with_season_intent_unions_and_resets_status(service):
    """Re-adding a show with new seasons + is_season_update unions seasons, resets status."""
    first, created = service.add(tmdb_id=701, media_type="show", selected_seasons=[1, 2])
    assert created is True
    first.status = "added"
    service.db.commit()

    existing, created2 = service.add(
        tmdb_id=701, media_type="show", selected_seasons=[2, 3], is_season_update=True
    )
    assert created2 is False
    assert existing.id == first.id
    assert existing.is_season_update is True
    assert json.loads(existing.selected_seasons) == [1, 2, 3]
    assert existing.status == "pending"


def test_readd_all_seasons_none_wins(service):
    """Re-adding with selected_seasons=None + is_season_update means 'all seasons' -> stored None."""
    service.add(tmdb_id=702, media_type="show", selected_seasons=[1, 2])
    existing, created = service.add(
        tmdb_id=702, media_type="show", selected_seasons=None, is_season_update=True
    )
    assert created is False
    assert existing.selected_seasons is None


def test_readd_into_all_seasons_stays_all(service):
    """Stored None ('all') unioned with a specific season stays 'all' -> None."""
    service.add(tmdb_id=703, media_type="show")  # stored None = all seasons
    existing, created = service.add(
        tmdb_id=703, media_type="show", selected_seasons=[3], is_season_update=True
    )
    assert created is False
    assert existing.selected_seasons is None


def test_readd_no_season_intent_leaves_unchanged(service):
    """Re-adding with no season intent leaves the existing row untouched, created False."""
    first, _ = service.add(tmdb_id=704, media_type="show", selected_seasons=[1, 2])
    first.status = "added"
    service.db.commit()

    existing, created = service.add(tmdb_id=704, media_type="show")
    assert created is False
    assert existing.status == "added"
    assert json.loads(existing.selected_seasons) == [1, 2]
    assert existing.is_season_update is False
