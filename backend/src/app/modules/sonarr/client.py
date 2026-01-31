"""Sonarr API client."""
import asyncio
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

    async def _put(self, endpoint: str, data: dict) -> Any:
        """Make PUT request to Sonarr API."""
        headers = {"X-Api-Key": self.api_key}
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            response = await client.put(
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
        selected_seasons: list[int] | None = None,
    ) -> dict:
        """Add series to Sonarr.

        Args:
            tmdb_id: TMDB ID of the series to add
            quality_profile_id: Quality profile ID (uses default if not specified)
            root_folder_path: Root folder path (uses first configured if not specified)
            selected_seasons: List of season numbers to monitor. If None, uses Sonarr
                defaults. If provided, only these seasons are monitored (season 0/specials
                are never auto-monitored regardless of selection).
        """
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

        # Apply season selection if provided
        if selected_seasons is not None and "seasons" in series:
            for season in series["seasons"]:
                season_num = season.get("seasonNumber", 0)
                # Season 0 (specials) are never auto-monitored
                if season_num == 0:
                    season["monitored"] = False
                else:
                    season["monitored"] = season_num in selected_seasons

        series["qualityProfileId"] = quality_profile_id
        series["rootFolderPath"] = root_folder_path
        series["monitored"] = True
        series["seasonFolder"] = True  # Ensure season folders are created
        series["addOptions"] = {"searchForMissingEpisodes": True}

        # Remove path if present - let Sonarr compute it from rootFolderPath + title
        # The lookup response may include an empty or incorrect path field
        series.pop("path", None)

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
        # Run all lookups concurrently for speed
        async def lookup_single(tmdb_id: int) -> tuple[int, str | None]:
            series = await self.lookup_series(tmdb_id)
            if series:
                tvdb_id = series.get("tvdbId")
                if tvdb_id and tvdb_id in tvdb_to_status:
                    return (tmdb_id, tvdb_to_status[tvdb_id])
            return (tmdb_id, None)

        lookups = await asyncio.gather(*[lookup_single(tid) for tid in tmdb_ids])
        return dict(lookups)

    async def get_queue(self) -> dict:
        """Get current download queue from Sonarr."""
        params = {
            "page": 1,
            "pageSize": 50,
            "includeSeries": True,
            "includeEpisode": True
        }
        return await self._get("/queue", params)

    async def get_recent(self, limit: int = 20) -> list:
        """Get recently added shows from Sonarr."""
        shows = await self._get("/series")

        # Sort by added date, most recent first
        shows.sort(key=lambda s: s.get("added", ""), reverse=True)

        return shows[:limit]

    async def get_series_details(self, tmdb_id: int) -> dict | None:
        """Get series details with season-level status from Sonarr library.

        Args:
            tmdb_id: TMDB ID of the series

        Returns:
            Dict with series info and season status, or None if not in library.
            Season status is one of:
            - "downloaded": All episodes have files (percentOfEpisodes == 100)
            - "monitored": Season is being monitored for download
            - "available": Season exists but not monitored
        """
        # Get TVDB ID from TMDB ID using lookup
        series_lookup = await self.lookup_series(tmdb_id)
        if not series_lookup:
            return None

        tvdb_id = series_lookup.get("tvdbId")
        if not tvdb_id:
            return None

        # Check if series is in library
        series = await self.get_series_by_tvdb_id(tvdb_id)
        if not series:
            return None

        # Build season status list
        seasons = []
        for season in series.get("seasons", []):
            season_num = season.get("seasonNumber", 0)

            # Skip specials (season 0)
            if season_num == 0:
                continue

            stats = season.get("statistics", {})
            episode_count = stats.get("episodeCount", 0)
            episode_file_count = stats.get("episodeFileCount", 0)
            percent = stats.get("percentOfEpisodes", 0)

            # Determine status
            if percent == 100:
                status = "downloaded"
            elif season.get("monitored", False):
                status = "monitored"
            else:
                status = "available"

            seasons.append({
                "number": season_num,
                "status": status,
                "episodes": f"{episode_file_count}/{episode_count}",
                "episode_count": episode_count,
                "episode_file_count": episode_file_count,
            })

        return {
            "in_library": True,
            "sonarr_id": series.get("id"),
            "title": series.get("title", ""),
            "seasons": seasons,
        }

    async def update_season_monitoring(self, tmdb_id: int, seasons_to_add: list[int]) -> dict:
        """Add monitoring for additional seasons and trigger search.

        Args:
            tmdb_id: TMDB ID of the series
            seasons_to_add: List of season numbers to start monitoring

        Returns:
            Updated series data from Sonarr
        """
        # Get TVDB ID
        series = await self.lookup_series(tmdb_id)
        if not series or not series.get("tvdbId"):
            raise ValueError(f"Series not found: {tmdb_id}")

        # Get existing series from library
        existing = await self.get_series_by_tvdb_id(series["tvdbId"])
        if not existing:
            raise ValueError(f"Series not in Sonarr library: {tmdb_id}")

        # Update season monitoring
        for season in existing.get("seasons", []):
            if season.get("seasonNumber") in seasons_to_add:
                season["monitored"] = True

        # PUT updated series
        updated = await self._put(f"/series/{existing['id']}", existing)

        # Trigger search for newly monitored seasons
        await self._post("/command", {
            "name": "SeriesSearch",
            "seriesId": existing["id"]
        })

        return updated
