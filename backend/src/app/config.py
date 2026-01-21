"""Application configuration via environment variables."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # TMDB
    tmdb_api_key: str = ""
    tmdb_base_url: str = "https://api.themoviedb.org/3"

    # Sonarr
    sonarr_url: str = "http://localhost:8989"
    sonarr_api_key: str = ""

    # Radarr
    radarr_url: str = "http://localhost:7878"
    radarr_api_key: str = ""

    # Database
    database_path: str = "./data/movie_discovery.db"

    model_config = SettingsConfigDict(
        # Look for .env in project root (parent of backend/)
        # Path: config.py → app → src → backend → movie_discovery (4 parents)
        env_file=Path(__file__).resolve().parent.parent.parent.parent / ".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
