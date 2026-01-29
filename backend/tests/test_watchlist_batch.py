"""Tests for watchlist batch processing endpoints."""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Watchlist  # noqa: F401
from app.database import Base, get_db
from app.main import app as fastapi_app


@pytest.fixture
def client():
    """Create a test client with an in-memory SQLite database."""
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
    yield TestClient(fastapi_app)
    fastapi_app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_batch_delete(client):
    """DELETE /api/watchlist/batch should remove multiple items."""
    # Add items
    client.post("/api/watchlist", json={
        "tmdb_id": 100,
        "media_type": "movie"
    })
    client.post("/api/watchlist", json={
        "tmdb_id": 101,
        "media_type": "movie"
    })

    # Delete batch
    response = client.request(
        "DELETE",
        "/api/watchlist/batch",
        json={"ids": [100, 101]}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["deleted"] == 2

    # Verify deletion
    response = client.get("/api/watchlist")
    assert response.json()["total"] == 0


def test_batch_delete_partial(client):
    """DELETE /api/watchlist/batch should handle partial matches."""
    # Add only one item
    client.post("/api/watchlist", json={
        "tmdb_id": 100,
        "media_type": "movie"
    })

    # Try to delete two (one doesn't exist)
    response = client.request(
        "DELETE",
        "/api/watchlist/batch",
        json={"ids": [100, 999]}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["deleted"] == 1


@patch("app.modules.radarr.client.RadarrClient.add_movie")
def test_batch_process_movies(mock_add_movie, client):
    """POST /api/watchlist/process should send movies to Radarr."""
    # Setup mock
    mock_add_movie.return_value = {"id": 1, "title": "Test"}

    # Add items to watchlist
    client.post("/api/watchlist", json={
        "tmdb_id": 603,
        "media_type": "movie"
    })
    client.post("/api/watchlist", json={
        "tmdb_id": 604,
        "media_type": "movie"
    })

    # Process batch
    response = client.post("/api/watchlist/process", json={
        "ids": [603, 604],
        "media_type": "movie"
    })
    assert response.status_code == 200
    data = response.json()
    assert "processed" in data
    assert "failed" in data
    assert 603 in data["processed"]
    assert 604 in data["processed"]


@patch("app.modules.sonarr.client.SonarrClient.add_series")
def test_batch_process_shows(mock_add_series, client):
    """POST /api/watchlist/process should send shows to Sonarr."""
    # Setup mock
    mock_add_series.return_value = {"id": 1, "title": "Test"}

    # Add items to watchlist
    client.post("/api/watchlist", json={
        "tmdb_id": 1399,
        "media_type": "tv"
    })

    # Process batch
    response = client.post("/api/watchlist/process", json={
        "ids": [1399],
        "media_type": "tv"
    })
    assert response.status_code == 200
    data = response.json()
    assert "processed" in data
    assert 1399 in data["processed"]


@patch("app.modules.radarr.client.RadarrClient.add_movie")
def test_batch_process_handles_errors(mock_add_movie, client):
    """POST /api/watchlist/process should report failures."""
    # Setup mock to fail
    mock_add_movie.side_effect = ValueError("Movie already in library")

    # Add item to watchlist
    client.post("/api/watchlist", json={
        "tmdb_id": 603,
        "media_type": "movie"
    })

    # Process batch
    response = client.post("/api/watchlist/process", json={
        "ids": [603],
        "media_type": "movie"
    })
    assert response.status_code == 200
    data = response.json()
    assert len(data["failed"]) == 1
    assert data["failed"][0]["tmdb_id"] == 603
    assert "already in library" in data["failed"][0]["error"]
