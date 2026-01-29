"""Tests for person detail endpoint."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestGetPerson:
    """Tests for GET /api/person/{person_id}."""

    def test_returns_person_details(self, client):
        """Should return person details with combined credits."""
        mock_response = {
            "id": 31,
            "name": "Tom Hanks",
            "biography": "An American actor and filmmaker.",
            "birthday": "1956-07-09",
            "place_of_birth": "Concord, California, USA",
            "profile_path": "/test.jpg",
            "combined_credits": {
                "cast": [
                    {"id": 13, "title": "Forrest Gump", "media_type": "movie"},
                    {"id": 862, "title": "Toy Story", "media_type": "movie"},
                ]
            },
        }

        with patch(
            "app.modules.discovery.router.tmdb_client.get_person",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = mock_response
            response = client.get("/api/discover/person/31")

        mock.assert_called_once_with(31)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 31
        assert data["name"] == "Tom Hanks"
        assert data["biography"] == "An American actor and filmmaker."
        assert "combined_credits" in data
        assert len(data["combined_credits"]["cast"]) == 2

    def test_returns_404_for_invalid_id(self, client):
        """Should return 404 for non-existent person."""
        with patch(
            "app.modules.discovery.router.tmdb_client.get_person",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = None
            response = client.get("/api/discover/person/999999999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Person not found"
