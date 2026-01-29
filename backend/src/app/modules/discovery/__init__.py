"""Discovery module - TMDB integration."""
from .tmdb_client import TMDBClient
from .router import router, genres_router

__all__ = ["TMDBClient", "router", "genres_router"]
