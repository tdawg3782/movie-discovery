"""Discovery module - TMDB integration."""
from .tmdb_client import TMDBClient
from .router import router

__all__ = ["TMDBClient", "router"]
