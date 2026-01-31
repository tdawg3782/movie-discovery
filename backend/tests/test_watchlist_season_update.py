# backend/tests/test_watchlist_season_update.py
"""Tests for watchlist season update field."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import Watchlist


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_watchlist_has_is_season_update_field(db):
    """Watchlist model has is_season_update field."""
    item = Watchlist(
        tmdb_id=1396,
        media_type="tv",
        selected_seasons="[4, 5]",
        is_season_update=True
    )
    db.add(item)
    db.commit()

    result = db.query(Watchlist).filter_by(tmdb_id=1396).first()
    assert result.is_season_update is True


def test_watchlist_is_season_update_defaults_false(db):
    """is_season_update defaults to False."""
    item = Watchlist(tmdb_id=1234, media_type="tv")
    db.add(item)
    db.commit()

    result = db.query(Watchlist).filter_by(tmdb_id=1234).first()
    assert result.is_season_update is False
