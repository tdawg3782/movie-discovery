"""Radarr API client."""
import httpx
from typing import Any


class RadarrClient:
    """Client for Radarr API."""

    def __init__(self, url: str, api_key: str):
        self.url = url.rstrip("/")
        self.api_key = api_key

    async def _get(self, endpoint: str, params: dict | None = None) -> Any:
        """Make GET request to Radarr API."""
        headers = {"X-Api-Key": self.api_key}
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            response = await client.get(
                f"{self.url}/api/v3{endpoint}",
                headers=headers,
                params=params,
            )
            response.raise_for_status()
            return response.json()

    async def _post(self, endpoint: str, data: dict) -> Any:
        """Make POST request to Radarr API."""
        headers = {"X-Api-Key": self.api_key}
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            response = await client.post(
                f"{self.url}/api/v3{endpoint}",
                headers=headers,
                json=data,
            )
            response.raise_for_status()
            return response.json()

    async def get_movie_by_tmdb_id(self, tmdb_id: int) -> dict | None:
        """Get movie from library by TMDB ID."""
        movies = await self._get("/movie", {"tmdbId": tmdb_id})
        return movies[0] if movies else None

    async def lookup_movie(self, tmdb_id: int) -> dict | None:
        """Lookup movie info from TMDB via Radarr."""
        results = await self._get("/movie/lookup", {"term": f"tmdb:{tmdb_id}"})
        return results[0] if results else None

    async def add_movie(
        self,
        tmdb_id: int,
        quality_profile_id: int = 1,
        root_folder_path: str | None = None,
    ) -> dict:
        """Add movie to Radarr."""
        movie = await self.lookup_movie(tmdb_id)
        if not movie:
            raise ValueError(f"Movie not found: {tmdb_id}")

        # Get root folder if not specified
        if not root_folder_path:
            folders = await self._get("/rootfolder")
            if not folders:
                raise ValueError("No root folders configured in Radarr")
            root_folder_path = folders[0]["path"]

        movie["qualityProfileId"] = quality_profile_id
        movie["rootFolderPath"] = root_folder_path
        movie["monitored"] = True
        movie["addOptions"] = {"searchForMovie": True}

        return await self._post("/movie", movie)

    async def get_status(self, tmdb_id: int) -> str:
        """Get movie status: 'available', 'added', or 'not_found'."""
        movie = await self.get_movie_by_tmdb_id(tmdb_id)
        if not movie:
            return "not_found"
        if movie.get("hasFile"):
            return "available"
        return "added"
