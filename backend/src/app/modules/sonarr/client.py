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

    async def get_quality_profiles(self) -> list:
        """Get available quality profiles."""
        return await self._get("/qualityprofile")

    async def add_series(
        self,
        tmdb_id: int,
        quality_profile_id: int | None = None,
        root_folder_path: str | None = None,
    ) -> dict:
        """Add series to Sonarr."""
        # Check if already in library
        series = await self.lookup_series(tmdb_id)
        if series and series.get("tvdbId"):
            existing = await self.get_series_by_tvdb_id(series["tvdbId"])
            if existing:
                raise ValueError(f"Series already in Sonarr library: {existing.get('title', tmdb_id)}")

        if not series:
            raise ValueError(f"Series not found: {tmdb_id}")

        if not root_folder_path:
            folders = await self._get("/rootfolder")
            if not folders:
                raise ValueError("No root folders configured in Sonarr")
            root_folder_path = folders[0]["path"]

        # Get quality profile if not specified
        if not quality_profile_id:
            profiles = await self.get_quality_profiles()
            if not profiles:
                raise ValueError("No quality profiles configured in Sonarr")
            quality_profile_id = profiles[0]["id"]

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

    async def get_all_series(self) -> list[dict]:
        """Get all series in library."""
        return await self._get("/series")

    async def get_batch_status(self, tmdb_ids: list[int]) -> dict[int, str | None]:
        """Get status for multiple series efficiently.

        Returns dict mapping tmdb_id -> status ('available', 'added', or None)

        Note: Sonarr uses TVDB IDs internally, so we need to check via TMDB ID
        stored in series data or fall back to lookup.
        """
        # Fetch all series once
        all_series = await self.get_all_series()

        # Build lookup by tvdb_id for series in library
        # Sonarr series have statistics that tell us if all episodes are downloaded
        tvdb_to_status = {}
        for series in all_series:
            tvdb_id = series.get("tvdbId")
            if tvdb_id:
                stats = series.get("statistics", {})
                if stats.get("percentOfEpisodes", 0) == 100:
                    tvdb_to_status[tvdb_id] = "available"
                else:
                    tvdb_to_status[tvdb_id] = "added"

        # For each requested TMDB ID, we need to find its TVDB ID
        # This requires looking up each one, but we can cache results
        results = {}
        for tmdb_id in tmdb_ids:
            # Look up series to get TVDB ID
            series = await self.lookup_series(tmdb_id)
            if series:
                tvdb_id = series.get("tvdbId")
                if tvdb_id and tvdb_id in tvdb_to_status:
                    results[tmdb_id] = tvdb_to_status[tvdb_id]
                else:
                    results[tmdb_id] = None
            else:
                results[tmdb_id] = None

        return results

    async def get_queue(self) -> dict:
        """Get current download queue from Sonarr."""
        params = {
            "page": 1,
            "pageSize": 50,
            "includeSeries": True,
            "includeEpisode": True
        }
        return await self._get("/queue", params)
