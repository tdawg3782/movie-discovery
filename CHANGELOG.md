# Changelog

All notable changes to Movie Discovery will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-01-29

### Added

- **Settings Module**
  - Configure API keys via UI (no more .env editing)
  - Test connection buttons for TMDB, Radarr, Sonarr
  - Encrypted storage for API keys
  - Auto-import from .env on first load

- **Discovery Filters**
  - Filter by genre (multi-select chips)
  - Filter by year range
  - Filter by minimum rating
  - Filter by content rating (G, PG, PG-13, R)
  - Sort by popularity, rating, or release date
  - Collapsible filter panel

- **Media Detail Pages**
  - Full movie/show detail view with backdrop
  - YouTube trailer playback in modal
  - Cast carousel with actor photos
  - "More Like This" recommendations
  - Collection links (MCU, Star Wars, etc.)

- **Person Pages**
  - Actor/director biography and photo
  - Complete filmography (movies and TV)
  - Click any cast member to view their page

- **Collection Pages**
  - Browse entire movie franchises
  - Sorted by release date
  - Links from movie detail pages

- **Watchlist Workflow Overhaul**
  - "Add" now sends to watchlist (not directly to library)
  - Batch selection with checkboxes
  - Batch processing (send multiple items to Radarr/Sonarr)
  - Batch delete
  - Status badges (Pending, In Library, Downloading)
  - Confirmation modal before processing

- **Library Monitor**
  - Recently Added tab (movies and shows)
  - Downloads tab with progress bars
  - Auto-refresh toggle (30s polling)
  - Combined activity feed from Radarr/Sonarr

- **Navigation**
  - New nav: Discover | Watchlist | Library | Settings
  - All detail pages accessible via poster clicks

### Changed

- Watchlist now serves as a staging queue before adding to library
- "Add" button behavior changed from instant-add to watchlist-first

### Endpoints Added

- `GET /api/settings` - Get settings (masked keys)
- `PUT /api/settings` - Update settings
- `POST /api/settings/test` - Test API connection
- `GET /api/genres/movies` - Movie genre list
- `GET /api/genres/shows` - TV genre list
- `GET /api/discover/movies?filters` - Filtered movie discovery
- `GET /api/discover/shows?filters` - Filtered show discovery
- `GET /api/discover/person/{id}` - Person details
- `GET /api/discover/movies/{id}` - Movie details with credits/videos
- `GET /api/discover/shows/{id}` - Show details with credits/videos
- `GET /api/discover/collection/{id}` - Collection details
- `POST /api/watchlist/process` - Batch process watchlist items
- `DELETE /api/watchlist/batch` - Batch delete watchlist items
- `GET /api/radarr/queue` - Movie download queue
- `GET /api/radarr/recent` - Recently added movies
- `GET /api/sonarr/queue` - TV download queue
- `GET /api/sonarr/recent` - Recently added shows
- `GET /api/library/activity` - Combined recent activity
- `GET /api/library/queue` - Combined download queue

---

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
