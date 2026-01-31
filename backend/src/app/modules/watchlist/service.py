"""Watchlist business logic."""
import json
from sqlalchemy.orm import Session

from app.models import Watchlist
from app.config import settings, get_setting
from app.modules.radarr.client import RadarrClient
from app.modules.sonarr.client import SonarrClient


class WatchlistService:
    """Service for managing watchlist items."""

    def __init__(self, db: Session):
        self.db = db

    def add(
        self,
        tmdb_id: int,
        media_type: str,
        notes: str | None = None,
        selected_seasons: list[int] | None = None,
        is_season_update: bool = False
    ) -> Watchlist:
        """Add item to watchlist. Returns existing if duplicate."""
        existing = (
            self.db.query(Watchlist)
            .filter(Watchlist.tmdb_id == tmdb_id, Watchlist.media_type == media_type)
            .first()
        )
        if existing:
            return existing

        # Convert seasons list to JSON string for storage
        seasons_json = json.dumps(selected_seasons) if selected_seasons is not None else None

        item = Watchlist(
            tmdb_id=tmdb_id,
            media_type=media_type,
            notes=notes,
            selected_seasons=seasons_json,
            is_season_update=is_season_update
        )
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

    def update_seasons(self, tmdb_id: int, selected_seasons: list[int] | None) -> Watchlist | None:
        """Update selected seasons for a watchlist item."""
        item = self.get_by_tmdb_id(tmdb_id)
        if not item:
            return None

        item.selected_seasons = json.dumps(selected_seasons) if selected_seasons is not None else None
        self.db.commit()
        self.db.refresh(item)
        return item

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
                    root_folder = get_setting("radarr_root_folder")
                    await client.add_movie(tmdb_id, root_folder_path=root_folder)
                else:
                    # Get watchlist item to retrieve selected seasons
                    item = self.get_by_tmdb_id(tmdb_id)
                    selected_seasons = None
                    if item and item.selected_seasons:
                        selected_seasons = json.loads(item.selected_seasons)

                    client = SonarrClient(settings.sonarr_url, settings.sonarr_api_key)
                    root_folder = get_setting("sonarr_root_folder")

                    if item and item.is_season_update:
                        # Update existing show's season monitoring
                        await client.update_season_monitoring(tmdb_id, selected_seasons)
                    else:
                        # Add new show
                        await client.add_series(tmdb_id, root_folder_path=root_folder, selected_seasons=selected_seasons)

                processed.append(tmdb_id)

                # Update watchlist item status
                item = self.get_by_tmdb_id(tmdb_id)
                if item:
                    item.status = "added"
                    self.db.commit()

            except Exception as e:
                failed.append({"tmdb_id": tmdb_id, "error": str(e)})

        return processed, failed
