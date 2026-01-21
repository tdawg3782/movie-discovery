"""Application configuration via environment variables."""
from pydantic_settings import BaseSettings


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

    class Config:
        env_file = ".env"


settings = Settings()
