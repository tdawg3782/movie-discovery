"""TMDB API client."""
import httpx
from typing import Any


class TMDBClient:
    """Client for The Movie Database API."""

    BASE_URL = "https://api.themoviedb.org/3"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def _get(self, endpoint: str, params: dict | None = None) -> dict[str, Any]:
        """Make GET request to TMDB API."""
        params = params or {}
        params["api_key"] = self.api_key

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.BASE_URL}{endpoint}", params=params)
            response.raise_for_status()
            return response.json()

    async def get_trending_movies(self, page: int = 1) -> dict[str, Any]:
        """Get trending movies."""
        return await self._get("/trending/movie/week", {"page": page})

    async def get_trending_shows(self, page: int = 1) -> dict[str, Any]:
        """Get trending TV shows."""
        return await self._get("/trending/tv/week", {"page": page})

    async def search(self, query: str, page: int = 1) -> dict[str, Any]:
        """Search for movies and TV shows."""
        return await self._get("/search/multi", {"query": query, "page": page})

    async def get_similar(self, tmdb_id: int, media_type: str) -> dict[str, Any]:
        """Get similar movies or shows."""
        endpoint = f"/{media_type}/{tmdb_id}/similar"
        return await self._get(endpoint)

    async def get_details(self, tmdb_id: int, media_type: str) -> dict[str, Any]:
        """Get movie or show details."""
        endpoint = f"/{media_type}/{tmdb_id}"
        return await self._get(endpoint)
