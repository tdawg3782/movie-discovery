"""Sonarr API client."""
import httpx
from typing import Any


class SonarrClient:
    """Client for Sonarr API."""

    def __init__(self, url: str, api_key: str):
        self.url = url.rstrip("/")
        self.api_key = api_key

    async def _get(self, endpoint: str, params: dict | None = None) -> Any:
        """Make GET request to Sonarr API."""
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
        """Make POST request to Sonarr API."""
        headers = {"X-Api-Key": self.api_key}
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            response = await client.post(
                f"{self.url}/api/v3{endpoint}",
                headers=headers,
                json=data,
            )
            response.raise_for_status()
            return response.json()

    async def get_series_by_tvdb_id(self, tvdb_id: int) -> dict | None:
        """Get series from library by TVDB ID."""
        series_list = await self._get("/series", {"tvdbId": tvdb_id})
        return series_list[0] if series_list else None

    async def lookup_series(self, tmdb_id: int) -> dict | None:
        """Lookup series info via Sonarr (uses TVDB internally)."""
        results = await self._get("/series/lookup", {"term": f"tmdb:{tmdb_id}"})
        return results[0] if results else None

    async def add_series(
        self,
        tmdb_id: int,
        quality_profile_id: int = 1,
        root_folder_path: str | None = None,
    ) -> dict:
        """Add series to Sonarr."""
        series = await self.lookup_series(tmdb_id)
        if not series:
            raise ValueError(f"Series not found: {tmdb_id}")

        if not root_folder_path:
            folders = await self._get("/rootfolder")
            if not folders:
                raise ValueError("No root folders configured in Sonarr")
            root_folder_path = folders[0]["path"]

        series["qualityProfileId"] = quality_profile_id
        series["rootFolderPath"] = root_folder_path
        series["monitored"] = True
        series["addOptions"] = {"searchForMissingEpisodes": True}

        return await self._post("/series", series)

    async def get_status(self, tmdb_id: int) -> str:
        """Get series status: 'available', 'added', or 'not_found'."""
        series = await self.lookup_series(tmdb_id)
        if not series:
            return "not_found"

        existing = await self.get_series_by_tvdb_id(series.get("tvdbId", 0))
        if not existing:
            return "not_found"

        stats = existing.get("statistics", {})
        if stats.get("percentOfEpisodes", 0) == 100:
            return "available"
        return "added"
