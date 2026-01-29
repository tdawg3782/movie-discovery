"""Tests for watchlist status field."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Watchlist
from app.database import Base


@pytest.fixture
def db_session():
    """Create a test database session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestSession()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def test_watchlist_has_status_field():
    """Watchlist model should have status field."""
    assert hasattr(Watchlist, "status")


def test_watchlist_status_default(db_session):
    """Watchlist status should default to 'pending'."""
    item = Watchlist(
        tmdb_id=123,
        media_type="movie",
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)

    assert item.status == "pending"


def test_watchlist_status_can_be_updated(db_session):
    """Watchlist status should be updatable."""
    item = Watchlist(
        tmdb_id=456,
        media_type="tv",
    )
    db_session.add(item)
    db_session.commit()

    item.status = "added"
    db_session.commit()
    db_session.refresh(item)

    assert item.status == "added"
