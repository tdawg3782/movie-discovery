"""Tests for discovery filter schemas."""
import pytest
from app.modules.discovery.schemas import DiscoveryFilters


class TestDiscoveryFilters:
    """Tests for DiscoveryFilters schema."""

    def test_filters_default_values(self):
        """Filters should have sensible defaults."""
        filters = DiscoveryFilters()
        assert filters.genre is None
        assert filters.year is None
        assert filters.rating_gte is None
        assert filters.sort_by == "popularity.desc"

    def test_filters_with_values(self):
        """Filters should accept all parameters."""
        filters = DiscoveryFilters(
            genre="28,12",
            year=2024,
            year_gte=2020,
            year_lte=2025,
            rating_gte=7.0,
            certification="PG-13",
            sort_by="vote_average.desc"
        )
        assert filters.genre == "28,12"
        assert filters.year == 2024
        assert filters.rating_gte == 7.0

    def test_filters_to_tmdb_params_movie(self):
        """Filters should convert to TMDB API params for movies."""
        filters = DiscoveryFilters(
            genre="28",
            year=2024,
            rating_gte=7.0,
            sort_by="popularity.desc"
        )
        params = filters.to_tmdb_params(media_type="movie")
        assert params["with_genres"] == "28"
        assert params["primary_release_year"] == 2024
        assert params["vote_average.gte"] == 7.0
        assert params["sort_by"] == "popularity.desc"

    def test_filters_to_tmdb_params_tv(self):
        """Filters should convert to TMDB API params for TV shows."""
        filters = DiscoveryFilters(
            genre="18",
            year=2023,
            year_gte=2020,
            year_lte=2025,
        )
        params = filters.to_tmdb_params(media_type="tv")
        assert params["with_genres"] == "18"
        assert params["first_air_date_year"] == 2023
        assert params["first_air_date.gte"] == "2020-01-01"
        assert params["first_air_date.lte"] == "2025-12-31"

    def test_filters_to_tmdb_params_certification(self):
        """Certification filter should include country."""
        filters = DiscoveryFilters(certification="R")
        params = filters.to_tmdb_params(media_type="movie")
        assert params["certification"] == "R"
        assert params["certification_country"] == "US"

    def test_filters_rating_adds_vote_count(self):
        """Rating filter should add minimum vote count."""
        filters = DiscoveryFilters(rating_gte=8.0)
        params = filters.to_tmdb_params(media_type="movie")
        assert params["vote_average.gte"] == 8.0
        assert params["vote_count.gte"] == 50
