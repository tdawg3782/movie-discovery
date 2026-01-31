"""Tests for watchlist API endpoints."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Import models FIRST to register them with Base.metadata
from app.models import Watchlist  # noqa: F401
from app.database import Base, get_db
from app.main import app as fastapi_app


@pytest.fixture
def client():
    """Create a test client with an in-memory SQLite database."""
    # Create test engine with StaticPool to share connection across threads
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create test session factory
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    # Override the dependency
    fastapi_app.dependency_overrides[get_db] = override_get_db

    yield TestClient(fastapi_app)

    # Cleanup
    fastapi_app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_add_to_watchlist(client):
    response = client.post(
        "/api/watchlist",
        json={"tmdb_id": 123, "media_type": "movie", "notes": "Want to watch"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["tmdb_id"] == 123


def test_get_watchlist(client):
    client.post("/api/watchlist", json={"tmdb_id": 123, "media_type": "movie"})
    client.post("/api/watchlist", json={"tmdb_id": 456, "media_type": "show"})

    response = client.get("/api/watchlist")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2


def test_delete_from_watchlist(client):
    add_response = client.post(
        "/api/watchlist", json={"tmdb_id": 123, "media_type": "movie"}
    )
    item_id = add_response.json()["id"]

    delete_response = client.delete(f"/api/watchlist/{item_id}")
    assert delete_response.status_code == 200

    get_response = client.get("/api/watchlist")
    assert get_response.json()["total"] == 0


def test_delete_nonexistent_returns_404(client):
    """Verify DELETE returns 404 for non-existent items."""
    response = client.delete("/api/watchlist/99999")
    assert response.status_code == 404


def test_get_watchlist_includes_status(client):
    """GET /api/watchlist should include status field."""
    client.post("/api/watchlist", json={
        "tmdb_id": 999,
        "media_type": "movie"
    })

    response = client.get("/api/watchlist")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) > 0
    assert "status" in data["items"][0]
    assert data["items"][0]["status"] == "pending"


@pytest.fixture
def db(client):
    """Get a database session for direct queries in tests."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    fastapi_app.dependency_overrides[get_db] = override_get_db
    session = TestSession()
    yield session
    session.close()


def test_add_to_watchlist_with_is_season_update(db):
    """Add to watchlist with is_season_update flag."""
    # Create a new client that uses the db fixture's session
    client = TestClient(fastapi_app)

    response = client.post("/api/watchlist", json={
        "tmdb_id": 1396,
        "media_type": "tv",
        "selected_seasons": [4, 5],
        "is_season_update": True
    })

    assert response.status_code == 201
    item = db.query(Watchlist).filter_by(tmdb_id=1396).first()
    assert item is not None
    assert item.is_season_update is True
