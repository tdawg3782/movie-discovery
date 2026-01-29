"""Discovery filter schemas."""
from typing import Optional
from pydantic import BaseModel, Field


class DiscoveryFilters(BaseModel):
    """Query parameters for discovery filtering."""

    genre: Optional[str] = Field(None, description="Comma-separated genre IDs")
    year: Optional[int] = Field(None, description="Exact release year")
    year_gte: Optional[int] = Field(None, description="Released on or after year")
    year_lte: Optional[int] = Field(None, description="Released on or before year")
    rating_gte: Optional[float] = Field(None, ge=0, le=10, description="Minimum rating")
    certification: Optional[str] = Field(None, description="Content rating (PG-13, R, etc)")
    sort_by: str = Field("popularity.desc", description="Sort order")

    def to_tmdb_params(self, media_type: str = "movie") -> dict:
        """Convert filters to TMDB API parameters."""
        params = {}

        if self.genre:
            params["with_genres"] = self.genre

        if self.sort_by:
            params["sort_by"] = self.sort_by

        if self.rating_gte is not None:
            params["vote_average.gte"] = self.rating_gte
            # Require minimum vote count to avoid obscure titles
            params["vote_count.gte"] = 50

        # Year handling differs by media type
        if media_type == "movie":
            if self.year:
                params["primary_release_year"] = self.year
            if self.year_gte:
                params["primary_release_date.gte"] = f"{self.year_gte}-01-01"
            if self.year_lte:
                params["primary_release_date.lte"] = f"{self.year_lte}-12-31"
        else:  # TV
            if self.year:
                params["first_air_date_year"] = self.year
            if self.year_gte:
                params["first_air_date.gte"] = f"{self.year_gte}-01-01"
            if self.year_lte:
                params["first_air_date.lte"] = f"{self.year_lte}-12-31"

        if self.certification:
            params["certification"] = self.certification
            params["certification_country"] = "US"

        return params
