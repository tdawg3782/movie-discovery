"""TMDB API client."""
import httpx
from typing import Any, Literal

from app.config import settings


class TMDBClientError(Exception):
    """Base exception for TMDB client errors."""

    pass


class TMDBNetworkError(TMDBClientError):
    """Raised when network request fails."""

    pass


class TMDBAPIError(TMDBClientError):
    """Raised when TMDB API returns an error."""

    pass


MediaType = Literal["movie", "tv"]


class TMDBClient:
    """Client for The Movie Database API."""

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        timeout: float = 10.0,
    ):
        self.api_key = api_key
        self.base_url = base_url or settings.tmdb_base_url
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "TMDBClient":
        """Enter async context."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context and close client."""
        await self.close()

    async def _get(self, endpoint: str, params: dict | None = None) -> dict[str, Any]:
        """Make GET request to TMDB API."""
        params = params or {}
        params["api_key"] = self.api_key
        url = f"{self.base_url}{endpoint}"

        try:
            client = await self._get_client()
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException as e:
            raise TMDBNetworkError(f"Request timed out: {url}") from e
        except httpx.ConnectError as e:
            raise TMDBNetworkError(f"Failed to connect to TMDB API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise TMDBAPIError(
                f"TMDB API error {e.response.status_code}: {e.response.text}"
            ) from e
        except Exception as e:
            raise TMDBClientError(f"Unexpected error: {e}") from e

    def _validate_media_type(self, media_type: str) -> MediaType:
        """Validate media_type is 'movie' or 'tv'."""
        if media_type not in ("movie", "tv"):
            raise ValueError(f"media_type must be 'movie' or 'tv', got '{media_type}'")
        return media_type  # type: ignore

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
        validated_type = self._validate_media_type(media_type)
        endpoint = f"/{validated_type}/{tmdb_id}/similar"
        return await self._get(endpoint)

    async def get_details(self, tmdb_id: int, media_type: str) -> dict[str, Any]:
        """Get movie or show details."""
        validated_type = self._validate_media_type(media_type)
        endpoint = f"/{validated_type}/{tmdb_id}"
        return await self._get(endpoint)

    async def get_movie_genres(self) -> dict[str, Any]:
        """Get list of movie genres from TMDB."""
        return await self._get("/genre/movie/list")

    async def get_tv_genres(self) -> dict[str, Any]:
        """Get list of TV genres from TMDB."""
        return await self._get("/genre/tv/list")

    async def discover_movies(self, page: int = 1, filters: dict | None = None) -> dict[str, Any]:
        """Discover movies with optional filters."""
        params = {
            "page": page,
            "include_adult": False,
        }
        if filters:
            params.update(filters)
        return await self._get("/discover/movie", params)

    async def discover_shows(self, page: int = 1, filters: dict | None = None) -> dict[str, Any]:
        """Discover TV shows with optional filters."""
        params = {
            "page": page,
            "include_adult": False,
        }
        if filters:
            params.update(filters)
        return await self._get("/discover/tv", params)

    async def get_person(self, person_id: int) -> dict[str, Any] | None:
        """Get person details with combined credits.

        Args:
            person_id: TMDB person ID.

        Returns:
            Person details dict or None if not found.
        """
        try:
            return await self._get(
                f"/person/{person_id}",
                {"append_to_response": "combined_credits"},
            )
        except TMDBAPIError as e:
            if "404" in str(e):
                return None
            raise

    async def get_movie_detail(self, movie_id: int) -> dict[str, Any] | None:
        """Get movie details with credits, videos, and recommendations.

        Args:
            movie_id: TMDB movie ID.

        Returns:
            Movie details dict or None if not found.
        """
        try:
            return await self._get(
                f"/movie/{movie_id}",
                {"append_to_response": "credits,videos,recommendations"},
            )
        except TMDBAPIError as e:
            if "404" in str(e):
                return None
            raise

    async def get_show_detail(self, show_id: int) -> dict[str, Any] | None:
        """Get TV show details with credits, videos, and recommendations.

        Args:
            show_id: TMDB show ID.

        Returns:
            Show details dict or None if not found.
        """
        try:
            return await self._get(
                f"/tv/{show_id}",
                {"append_to_response": "credits,videos,recommendations"},
            )
        except TMDBAPIError as e:
            if "404" in str(e):
                return None
            raise

    async def get_collection(self, collection_id: int) -> dict[str, Any] | None:
        """Get collection details with all movies.

        Args:
            collection_id: TMDB collection ID.

        Returns:
            Collection details dict or None if not found.
        """
        try:
            return await self._get(f"/collection/{collection_id}")
        except TMDBAPIError as e:
            if "404" in str(e):
                return None
            raise
