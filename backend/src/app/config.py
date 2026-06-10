"""Application configuration via environment variables."""
import logging
from pathlib import Path
from typing import Optional

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

    # Cloudflare (optional, used for deployment)
    cloudflare_tunnel_token: str = ""

    model_config = SettingsConfigDict(
        # Look for .env in project root (parent of backend/)
        # Path: config.py → app → src → backend → movie_discovery (4 parents)
        env_file=Path(__file__).resolve().parent.parent.parent.parent / ".env",
        env_file_encoding="utf-8",
    )


settings = Settings()


def get_setting(key: str) -> Optional[str]:
    """Get a setting value, checking database first, then .env fallback."""
    from app.database import SessionLocal
    from app.modules.settings.service import SettingsService
    from sqlalchemy.exc import SQLAlchemyError
    from cryptography.fernet import InvalidToken

    db = SessionLocal()
    try:
        value = SettingsService(db).get_raw_value(key)
        if value:
            return value
    except (SQLAlchemyError, InvalidToken) as exc:
        logging.getLogger(__name__).warning(
            "get_setting(%s) DB lookup failed: %s", key, exc
        )
    finally:
        db.close()

    # Fallback to .env
    env_value = getattr(settings, key, None)
    return env_value if env_value else None
