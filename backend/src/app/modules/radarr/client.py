"""Radarr API client."""
from app.modules.arr_base import BaseArrClient


class RadarrClient(BaseArrClient):
    """Client for Radarr API."""

    async def get_movie_by_tmdb_id(self, tmdb_id: int) -> dict | None:
        """Get movie from library by TMDB ID."""
        movies = await self._get("/movie", {"tmdbId": tmdb_id})
        return movies[0] if movies else None

    async def lookup_movie(self, tmdb_id: int) -> dict | None:
        """Lookup movie info from TMDB via Radarr."""
        results = await self._get("/movie/lookup", {"term": f"tmdb:{tmdb_id}"})
        return results[0] if results else None

    async def get_quality_profiles(self) -> list:
        """Get available quality profiles."""
        return await self._get("/qualityprofile")

    async def add_movie(
        self,
        tmdb_id: int,
        quality_profile_id: int | None = None,
        root_folder_path: str | None = None,
    ) -> dict:
        """Add movie to Radarr."""
        existing = await self.get_movie_by_tmdb_id(tmdb_id)
        if existing:
            raise ValueError(f"Movie already in Radarr library: {existing.get('title', tmdb_id)}")

        movie = await self.lookup_movie(tmdb_id)
        if not movie:
            raise ValueError(f"Movie not found: {tmdb_id}")

        if not root_folder_path:
            folders = await self._get("/rootfolder")
            if not folders:
                raise ValueError("No root folders configured in Radarr")
            root_folder_path = folders[0]["path"]

        if not quality_profile_id:
            profiles = await self.get_quality_profiles()
            if not profiles:
                raise ValueError("No quality profiles configured in Radarr")
            quality_profile_id = profiles[0]["id"]

        movie["qualityProfileId"] = quality_profile_id
        movie["rootFolderPath"] = root_folder_path
        movie["monitored"] = True
        movie["addOptions"] = {"searchForMovie": True}
        movie.pop("path", None)

        return await self._post("/movie", movie)

    async def get_status(self, tmdb_id: int) -> str:
        """Get movie status: 'available', 'added', or 'not_found'."""
        movie = await self.get_movie_by_tmdb_id(tmdb_id)
        if not movie:
            return "not_found"
        if movie.get("hasFile"):
            return "available"
        return "added"

    async def get_all_movies(self) -> list[dict]:
        """Get all movies in library."""
        return await self._get("/movie")

    async def get_batch_status(self, tmdb_ids: list[int]) -> dict[int, str]:
        """Get status for multiple movies efficiently."""
        all_movies = await self.get_all_movies()

        library_map = {}
        for movie in all_movies:
            tmdb_id = movie.get("tmdbId")
            if tmdb_id:
                if movie.get("hasFile"):
                    library_map[tmdb_id] = "available"
                else:
                    library_map[tmdb_id] = "added"

        return {tmdb_id: library_map.get(tmdb_id) for tmdb_id in tmdb_ids}

    async def get_queue(self) -> dict:
        """Get current download queue from Radarr."""
        return await self._get("/queue", {
            "page": 1,
            "pageSize": 50,
            "includeMovie": True,
        })

    async def get_recent(self, limit: int = 20) -> list:
        """Get recently added movies from Radarr."""
        movies = await self._get("/movie")
        movies.sort(key=lambda m: m.get("added", ""), reverse=True)
        return [m for m in movies if m.get("hasFile")][:limit]
