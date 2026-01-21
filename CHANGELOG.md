# Changelog

All notable changes to Movie Discovery will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-01-21

### Added

- **Discovery Module**
  - Browse trending movies from TMDB
  - Browse trending TV shows from TMDB
  - Search for any movie or TV show
  - Pagination with "Load More" button
  - Mixed search results (movies and shows together)

- **Radarr Integration**
  - Check movie library status
  - One-click add movies to Radarr
  - Auto-detect quality profile (uses first available)
  - Clear error messages for duplicates

- **Sonarr Integration**
  - Check TV show library status
  - One-click add shows to Sonarr
  - Auto-detect quality profile (uses first available)
  - Clear error messages for duplicates

- **Watchlist Module**
  - Save movies/shows to review later
  - Add notes to watchlist items
  - Remove items from watchlist
  - Persistent storage in SQLite

- **Frontend**
  - Vue 3 with Composition API
  - Dark theme UI
  - Responsive media grid
  - Search bar with clear button
  - Movies/Shows tab switching
  - Loading states and error handling

- **Infrastructure**
  - FastAPI backend with modular architecture
  - SQLite database for watchlist
  - Environment-based configuration
  - `start.bat` and `stop.bat` scripts for Windows
  - 75 backend tests with full coverage

### Fixed

- Config now loads `.env` from project root (not backend directory)
- Frontend properly handles axios response unwrapping
- Quality profile auto-detection for Radarr/Sonarr (no hardcoded ID)
- Router no longer overrides quality profile with invalid default

### Configuration

- Frontend runs on port 3000 (configurable in vite.config.js)
- Backend runs on port 8000
- CORS configured for localhost:3000

## [Unreleased]

### Planned
- Library status badges on media cards
- Similar movies/shows recommendations
- Bulk add to library
- Filter by genre
- Sort options (popularity, rating, date)
