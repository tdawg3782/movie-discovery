"""SQLAlchemy database models."""
from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Settings(Base):
    """Application settings stored in database."""

    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    value: Mapped[str] = mapped_column(Text)
    encrypted: Mapped[bool] = mapped_column(Boolean, default=False)


class MediaCache(Base):
    """Cached metadata from TMDB."""

    __tablename__ = "media_cache"

    id: Mapped[int] = mapped_column(primary_key=True)
    tmdb_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    media_type: Mapped[str] = mapped_column(String(10))  # 'movie' or 'show'
    title: Mapped[str] = mapped_column(String(255))
    overview: Mapped[str | None] = mapped_column(Text, nullable=True)
    poster_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    release_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    vote_average: Mapped[float | None] = mapped_column(Float, nullable=True)
    cached_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Watchlist(Base):
    """User's watchlist items."""

    __tablename__ = "watchlist"

    id: Mapped[int] = mapped_column(primary_key=True)
    tmdb_id: Mapped[int] = mapped_column(Integer, index=True)
    media_type: Mapped[str] = mapped_column(String(10))
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, added, downloading
    selected_seasons: Mapped[str | None] = mapped_column(Text, nullable=True)
    # JSON array like "[1, 2, 3]" or null for all seasons
    is_season_update: Mapped[bool] = mapped_column(Boolean, default=False)
    # True when adding seasons to existing show in Sonarr

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )


class LibraryStatus(Base):
    """Track items added to Sonarr/Radarr."""

    __tablename__ = "library_status"

    id: Mapped[int] = mapped_column(primary_key=True)
    tmdb_id: Mapped[int] = mapped_column(Integer, index=True)
    media_type: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20))  # 'added', 'downloading', 'available'
    checked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )
