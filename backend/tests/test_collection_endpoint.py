"""Tests for collection endpoint."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestGetCollection:
    """Tests for GET /api/discover/collection/{collection_id}."""

    def test_returns_collection_details(self, client):
        """Should return collection details with all movies."""
        mock_response = {
            "id": 2344,
            "name": "The Matrix Collection",
            "overview": "The Matrix trilogy follows Neo's journey.",
            "poster_path": "/matrix_collection.jpg",
            "backdrop_path": "/matrix_collection_bg.jpg",
            "parts": [
                {"id": 603, "title": "The Matrix", "release_date": "1999-03-30"},
                {"id": 604, "title": "The Matrix Reloaded", "release_date": "2003-05-15"},
                {"id": 605, "title": "The Matrix Revolutions", "release_date": "2003-11-05"},
            ],
        }

        with patch(
            "app.modules.discovery.router.tmdb_client.get_collection",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = mock_response
            response = client.get("/api/discover/collection/2344")

        mock.assert_called_once_with(2344)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 2344
        assert data["name"] == "The Matrix Collection"
        assert "parts" in data
        assert isinstance(data["parts"], list)
        assert len(data["parts"]) == 3

    def test_returns_404_for_invalid_id(self, client):
        """Should return 404 for non-existent collection."""
        with patch(
            "app.modules.discovery.router.tmdb_client.get_collection",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = None
            response = client.get("/api/discover/collection/999999999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Collection not found"
