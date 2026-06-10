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
from app.modules.watchlist.router import _parse_seasons
from unittest.mock import patch, AsyncMock
from app.modules.discovery.tmdb_client import TMDBAPIError, TMDBNetworkError


@pytest.fixture(autouse=True)
def mock_get_details():
    """Make watchlist enrichment deterministic: get_details succeeds by default.

    Yields the AsyncMock so a test can override .side_effect to drive the
    404-placeholder or outage-502 paths. The patch is stopped after each test.
    """
    with patch(
        "app.modules.clients.tmdb_client.get_details",
        new_callable=AsyncMock,
        return_value={
            "title": "Mock",
            "name": "Mock",
            "overview": "",
            "poster_path": None,
            "release_date": None,
            "first_air_date": None,
            "vote_average": 1.0,
            "number_of_seasons": 1,
        },
    ) as mock:
        yield mock


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


def test_update_details_sets_priority_and_notes(client):
    """PATCH details with priority+notes returns 200 and applies both."""
    add = client.post("/api/watchlist", json={"tmdb_id": 555, "media_type": "movie"})
    item_id = add.json()["id"]
    response = client.patch(f"/api/watchlist/{item_id}/details", json={"priority": 1, "notes": "soon"})
    assert response.status_code == 200
    data = response.json()
    assert data["priority"] == 1
    assert data["notes"] == "soon"


def test_update_details_partial_preserves_priority(client):
    """Follow-up PATCH with only tags preserves prior priority."""
    add = client.post("/api/watchlist", json={"tmdb_id": 556, "media_type": "movie"})
    item_id = add.json()["id"]
    client.patch(f"/api/watchlist/{item_id}/details", json={"priority": 1, "notes": "soon"})
    response = client.patch(f"/api/watchlist/{item_id}/details", json={"tags": ["docu"]})
    assert response.status_code == 200
    data = response.json()
    assert data["priority"] == 1
    assert data["tags"] == ["docu"]


def test_update_details_unknown_id_returns_404(client):
    """PATCH details for unknown id returns 404."""
    response = client.patch("/api/watchlist/99999/details", json={"priority": 1})
    assert response.status_code == 404


def test_get_watchlist_items_include_priority_and_tags(client):
    """GET items carry priority and tags keys."""
    client.post("/api/watchlist", json={"tmdb_id": 557, "media_type": "movie"})
    response = client.get("/api/watchlist")
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert "priority" in item
    assert "tags" in item


def test_readd_with_season_intent_returns_200(client):
    """Re-adding an existing show with season intent returns 200, not 201."""
    first = client.post("/api/watchlist", json={
        "tmdb_id": 1399, "media_type": "show", "selected_seasons": [1, 2]
    })
    assert first.status_code == 201

    second = client.post("/api/watchlist", json={
        "tmdb_id": 1399, "media_type": "show",
        "selected_seasons": [3], "is_season_update": True
    })
    assert second.status_code == 200
    assert second.json()["tmdb_id"] == 1399


def test_first_add_returns_201_and_persists(client):
    """First-time add returns 201 and the row is persisted."""
    response = client.post("/api/watchlist", json={"tmdb_id": 1400, "media_type": "movie"})
    assert response.status_code == 201
    listing = client.get("/api/watchlist")
    assert any(i["tmdb_id"] == 1400 for i in listing.json()["items"])


def test_parse_seasons_quoted_string_returns_none():
    assert _parse_seasons('"5"') is None


def test_parse_seasons_bare_int_returns_none():
    assert _parse_seasons('5') is None


def test_parse_seasons_list_returns_list():
    assert _parse_seasons('[1, 2]') == [1, 2]

def test_enrich_404_yields_placeholder(client, mock_get_details):
    """A genuine TMDB 404 degrades the row to the TMDB:{id} placeholder at 200."""
    client.post("/api/watchlist", json={"tmdb_id": 777, "media_type": "movie"})
    mock_get_details.side_effect = TMDBAPIError("missing", status_code=404)

    response = client.get("/api/watchlist")
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["title"] == "TMDB:777"


def test_get_watchlist_502_on_tmdb_outage(client, mock_get_details):
    """A TMDB outage surfaces as 502, not a list of placeholder rows."""
    client.post("/api/watchlist", json={"tmdb_id": 778, "media_type": "movie"})
    mock_get_details.side_effect = TMDBNetworkError("boom")

    response = client.get("/api/watchlist")
    assert response.status_code == 502


def test_add_to_watchlist_502_on_tmdb_outage(client, mock_get_details):
    """POST enrichment under a TMDB outage returns 502, not a placeholder row."""
    mock_get_details.side_effect = TMDBNetworkError("boom")

    response = client.post("/api/watchlist", json={"tmdb_id": 779, "media_type": "movie"})
    assert response.status_code == 502
