"""Discovery API routes."""
from fastapi import APIRouter, Query

from app.config import settings
from app.schemas import MediaList, MediaResponse
from .tmdb_client import TMDBClient

router = APIRouter(prefix="/api/discover", tags=["discovery"])

tmdb_client = TMDBClient(api_key=settings.tmdb_api_key)


def _transform_tmdb_result(item: dict, media_type: str | None = None) -> MediaResponse:
    """Transform TMDB result to our schema.

    Args:
        item: Raw TMDB result dict.
        media_type: Override media type (use for trending endpoints where type is known).

    Returns:
        MediaResponse with standardized fields.
    """
    mtype = media_type or item.get("media_type", "movie")
    # TV shows use "name" instead of "title"
    title = item.get("title") or item.get("name", "Unknown")
    # TV shows use "first_air_date" instead of "release_date"
    release = item.get("release_date") or item.get("first_air_date")

    return MediaResponse(
        tmdb_id=item["id"],
        media_type=mtype,
        title=title,
        overview=item.get("overview"),
        poster_path=item.get("poster_path"),
        release_date=release,
        vote_average=item.get("vote_average"),
        library_status=None,
    )


@router.get("/movies/trending", response_model=MediaList)
async def get_trending_movies(page: int = Query(1, ge=1)):
    """Get trending movies from TMDB.

    Args:
        page: Page number (default 1).

    Returns:
        MediaList with trending movies.
    """
    data = await tmdb_client.get_trending_movies(page=page)
    return MediaList(
        results=[_transform_tmdb_result(item, "movie") for item in data["results"]],
        page=data["page"],
        total_pages=data["total_pages"],
        total_results=data["total_results"],
    )


@router.get("/shows/trending", response_model=MediaList)
async def get_trending_shows(page: int = Query(1, ge=1)):
    """Get trending TV shows from TMDB.

    Args:
        page: Page number (default 1).

    Returns:
        MediaList with trending TV shows.
    """
    data = await tmdb_client.get_trending_shows(page=page)
    return MediaList(
        results=[_transform_tmdb_result(item, "show") for item in data["results"]],
        page=data["page"],
        total_pages=data["total_pages"],
        total_results=data["total_results"],
    )


@router.get("/search", response_model=MediaList)
async def search(q: str = Query(..., min_length=1), page: int = Query(1, ge=1)):
    """Search for movies and TV shows.

    Args:
        q: Search query string.
        page: Page number (default 1).

    Returns:
        MediaList with search results (movies and TV shows only).
    """
    data = await tmdb_client.search(query=q, page=page)
    # Filter to only movies and TV shows (exclude people, etc.)
    # Convert "tv" media_type to "show" for consistency
    results = []
    for item in data["results"]:
        item_type = item.get("media_type")
        if item_type == "movie":
            results.append(_transform_tmdb_result(item, "movie"))
        elif item_type == "tv":
            results.append(_transform_tmdb_result(item, "show"))
        # Skip "person" and other types

    return MediaList(
        results=results,
        page=data["page"],
        total_pages=data["total_pages"],
        total_results=len(results),
    )


@router.get("/similar/{tmdb_id}", response_model=MediaList)
async def get_similar(tmdb_id: int, media_type: str = Query(...)):
    """Get similar movies or shows.

    Args:
        tmdb_id: TMDB ID of the media.
        media_type: Type of media ('movie' or 'show').

    Returns:
        MediaList with similar items.
    """
    # Convert "show" to "tv" for TMDB API
    api_media_type = "tv" if media_type == "show" else media_type
    data = await tmdb_client.get_similar(tmdb_id=tmdb_id, media_type=api_media_type)
    return MediaList(
        results=[_transform_tmdb_result(item, media_type) for item in data["results"]],
        page=1,
        total_pages=1,
        total_results=len(data["results"]),
    )
