"""Watchlist business logic."""
from sqlalchemy.orm import Session

from app.models import Watchlist
from app.config import settings
from app.modules.radarr.client import RadarrClient
from app.modules.sonarr.client import SonarrClient


class WatchlistService:
    """Service for managing watchlist items."""

    def __init__(self, db: Session):
        self.db = db

    def add(self, tmdb_id: int, media_type: str, notes: str | None = None) -> Watchlist:
        """Add item to watchlist. Returns existing if duplicate."""
        existing = (
            self.db.query(Watchlist)
            .filter(Watchlist.tmdb_id == tmdb_id, Watchlist.media_type == media_type)
            .first()
        )
        if existing:
            return existing

        item = Watchlist(tmdb_id=tmdb_id, media_type=media_type, notes=notes)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def get_all(self) -> list[Watchlist]:
        """Get all watchlist items."""
        return self.db.query(Watchlist).order_by(Watchlist.added_at.desc()).all()

    def get_by_id(self, item_id: int) -> Watchlist | None:
        """Get watchlist item by ID."""
        return self.db.query(Watchlist).filter(Watchlist.id == item_id).first()

    def get_by_tmdb_id(self, tmdb_id: int) -> Watchlist | None:
        """Get watchlist item by TMDB ID."""
        return self.db.query(Watchlist).filter(Watchlist.tmdb_id == tmdb_id).first()

    def remove(self, item_id: int) -> bool:
        """Remove item from watchlist."""
        item = self.get_by_id(item_id)
        if not item:
            return False
        self.db.delete(item)
        self.db.commit()
        return True

    def delete_batch(self, tmdb_ids: list[int]) -> int:
        """Delete multiple watchlist items by TMDB ID. Returns count deleted."""
        deleted = (
            self.db.query(Watchlist)
            .filter(Watchlist.tmdb_id.in_(tmdb_ids))
            .delete(synchronize_session=False)
        )
        self.db.commit()
        return deleted

    async def process_batch(
        self, tmdb_ids: list[int], media_type: str
    ) -> tuple[list[int], list[dict]]:
        """
        Process watchlist items by sending to Radarr/Sonarr.
        Returns (processed_ids, failed_items).
        """
        processed = []
        failed = []

        for tmdb_id in tmdb_ids:
            try:
                if media_type == "movie":
                    client = RadarrClient(settings.radarr_url, settings.radarr_api_key)
                    await client.add_movie(tmdb_id)
                else:
                    client = SonarrClient(settings.sonarr_url, settings.sonarr_api_key)
                    await client.add_series(tmdb_id)

                processed.append(tmdb_id)

                # Update watchlist item status
                item = self.get_by_tmdb_id(tmdb_id)
                if item:
                    item.status = "added"
                    self.db.commit()

            except Exception as e:
                failed.append({"tmdb_id": tmdb_id, "error": str(e)})

        return processed, failed
