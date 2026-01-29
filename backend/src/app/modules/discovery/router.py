"""Discovery API routes."""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from app.config import settings
from app.schemas import MediaList, MediaResponse
from .tmdb_client import TMDBClient
from .schemas import DiscoveryFilters

router = APIRouter(prefix="/api/discover", tags=["discovery"])
genres_router = APIRouter(prefix="/api/genres", tags=["genres"])

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


@router.get("/movies", response_model=MediaList)
async def discover_movies(
    page: int = Query(1, ge=1),
    genre: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    year_gte: Optional[int] = Query(None),
    year_lte: Optional[int] = Query(None),
    rating_gte: Optional[float] = Query(None, ge=0, le=10),
    certification: Optional[str] = Query(None),
    sort_by: str = Query("popularity.desc"),
):
    """Discover movies with filters.

    Args:
        page: Page number (default 1).
        genre: Comma-separated genre IDs.
        year: Exact release year.
        year_gte: Released on or after year.
        year_lte: Released on or before year.
        rating_gte: Minimum rating (0-10).
        certification: Content rating (G, PG, PG-13, R).
        sort_by: Sort order (default: popularity.desc).

    Returns:
        MediaList with filtered movies.
    """
    filters = DiscoveryFilters(
        genre=genre,
        year=year,
        year_gte=year_gte,
        year_lte=year_lte,
        rating_gte=rating_gte,
        certification=certification,
        sort_by=sort_by,
    )
    data = await tmdb_client.discover_movies(page=page, filters=filters.to_tmdb_params("movie"))
    return MediaList(
        results=[_transform_tmdb_result(item, "movie") for item in data["results"]],
        page=data["page"],
        total_pages=data["total_pages"],
        total_results=data["total_results"],
    )


@router.get("/shows", response_model=MediaList)
async def discover_shows(
    page: int = Query(1, ge=1),
    genre: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    year_gte: Optional[int] = Query(None),
    year_lte: Optional[int] = Query(None),
    rating_gte: Optional[float] = Query(None, ge=0, le=10),
    sort_by: str = Query("popularity.desc"),
):
    """Discover TV shows with filters.

    Args:
        page: Page number (default 1).
        genre: Comma-separated genre IDs.
        year: Exact first air year.
        year_gte: First aired on or after year.
        year_lte: First aired on or before year.
        rating_gte: Minimum rating (0-10).
        sort_by: Sort order (default: popularity.desc).

    Returns:
        MediaList with filtered TV shows.
    """
    filters = DiscoveryFilters(
        genre=genre,
        year=year,
        year_gte=year_gte,
        year_lte=year_lte,
        rating_gte=rating_gte,
        sort_by=sort_by,
    )
    data = await tmdb_client.discover_shows(page=page, filters=filters.to_tmdb_params("tv"))
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


# Genre endpoints
@genres_router.get("/movies")
async def get_movie_genres():
    """Get list of movie genres."""
    return await tmdb_client.get_movie_genres()


@genres_router.get("/shows")
async def get_tv_genres():
    """Get list of TV show genres."""
    return await tmdb_client.get_tv_genres()


# Detail endpoints
@router.get("/person/{person_id}")
async def get_person(person_id: int):
    """Get person details with filmography.

    Args:
        person_id: TMDB person ID.

    Returns:
        Person details with combined credits.
    """
    data = await tmdb_client.get_person(person_id)
    if not data:
        raise HTTPException(status_code=404, detail="Person not found")
    return data


@router.get("/movies/{movie_id}")
async def get_movie_detail(movie_id: int):
    """Get movie details with cast, videos, and recommendations.

    Args:
        movie_id: TMDB movie ID.

    Returns:
        Movie details with credits, videos, and recommendations.
    """
    data = await tmdb_client.get_movie_detail(movie_id)
    if not data:
        raise HTTPException(status_code=404, detail="Movie not found")
    return data


@router.get("/shows/{show_id}")
async def get_show_detail(show_id: int):
    """Get TV show details with cast, videos, and recommendations.

    Args:
        show_id: TMDB show ID.

    Returns:
        Show details with credits, videos, and recommendations.
    """
    data = await tmdb_client.get_show_detail(show_id)
    if not data:
        raise HTTPException(status_code=404, detail="Show not found")
    return data


@router.get("/collection/{collection_id}")
async def get_collection(collection_id: int):
    """Get collection details with all movies.

    Args:
        collection_id: TMDB collection ID.

    Returns:
        Collection details with all movies in the collection.
    """
    data = await tmdb_client.get_collection(collection_id)
    if not data:
        raise HTTPException(status_code=404, detail="Collection not found")
    return data
