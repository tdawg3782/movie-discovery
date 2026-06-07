# Changelog

All notable changes to Movie Discovery will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.9.0] - 2026-06-06

### Added

- **Streaming availability ("Where to Watch") on detail pages**
  - Movie and show detail pages now show where the title can be streamed for a configurable region, so you can decide whether to download it or just stream it
  - Providers come from TMDB and piggyback on the existing detail request (no extra API call); only subscription (`flatrate`) and free/ad-supported services are shown — pay-per-title rent/buy are excluded — and duplicates are merged
  - When a region has no providers, the section is simply hidden (no error)
  - New `streaming_region` setting (two-letter country code, default `US`, editable in Settings; leave empty to revert to US)
  - New presentational `WatchProviders.vue` component renders the provider logos linking out to TMDB's watch page
  - Scope note: the poster-badge surface mentioned in the roadmap was deferred (TMDB list endpoints carry no provider data, so a badge would cost one extra call per card) and remains a backlog idea

---

## [2.8.0] - 2026-06-06

### Added

- **Watchlist sort & filter**
  - Sort the watchlist by date added, title, rating, or release date, in either direction; items missing a sort key (no rating / no release date) always sort last instead of floating to the top
  - Filter by media type (All / Movies / TV Shows) and by status (All / Pending / In Library / Downloading); the media-type tabs are now state-driven
  - The chosen sort and filters are mirrored into the URL query string, so the view survives a reload and the browser Back button (defaults are omitted, keeping a pristine watchlist URL clean)
  - New pure, unit-tested `watchlistState` module (`parseWatchlistState` / `serializeWatchlistState` / `applyWatchlistView`); `WatchlistView.vue` is now thin glue over it

---

## [2.7.0] - 2026-06-06

### Added

- **Paginated Discover with restored position**
  - Numbered page navigation (Prev / "Page X of Y" / Next) replaces the "Load More" button on the Discover page
  - Active tab, page, search query, and filters are mirrored into the URL query string; a reload or the browser Back button (e.g. from a detail page) restores the exact tab, page, search, and filter chips
  - New `PaginationControls` component plus a pure, unit-tested `discoverState` URL-state module (`parseDiscoverState` / `serializeDiscoverState` / `clampPage`)
  - Added a Vitest test harness for the frontend (`npm run test`)

### Changed

- **Discover feed no longer appends pages** — each page replaces the previous results; switching tabs clears the media-type-specific genre filter so the URL, API request, and filter panel stay in sync
- Known limitation (unchanged): the In Library / Not in Library filters still run client-side per page, so paginated pages can look unevenly filled (server-side library filtering remains a backlog item)

---

## [2.6.0] - 2026-06-06

### Added

- **Default Quality Profile Configuration**
  - Choose a default Radarr/Sonarr quality profile in the Settings UI (dropdowns under each Root Folder field)
  - New settings: `radarr_quality_profile_id` and `sonarr_quality_profile_id` (stored as plain, clearable strings)
  - Batch-added movies/shows now use the chosen profile instead of the `*arr` API's first profile (often "Any"/"SD")
  - Leaving a dropdown on "Use default" reverts to the auto-first-profile fallback
  - New endpoints: `GET /api/radarr/quality-profiles` and `GET /api/sonarr/quality-profiles` to populate the dropdowns

### Fixed

- **Partial settings updates** no longer wipe other saved clearable settings — `update_settings` now processes only the fields the caller actually provides (`model_dump(exclude_unset=True)`); an explicit blank value still clears

---

## [2.5.0] - 2026-03-28

### Changed

- **Shared HTTP Client for Radarr/Sonarr**
  - Extracted `BaseArrClient` base class with persistent `httpx.AsyncClient`
  - Radarr/Sonarr clients now reuse TCP connections instead of creating one per API call
  - Reduces latency and connection overhead, especially during batch operations

- **Parallelized Batch Processing**
  - Backend: `process_batch` now uses `asyncio.gather()` instead of sequential loop
  - Frontend: movie and show processing run in parallel via `Promise.all()`
  - Client and settings cached outside loop to avoid redundant creation

- **Deduplicated Watchlist Enrichment**
  - Extracted `_enrich_watchlist_item()` and `_parse_seasons()` shared helpers
  - Eliminated ~80 lines of copy-pasted TMDB enrichment logic in watchlist router

- **Simplified TMDB Client**
  - Added `_get_or_none()` method for 404 handling (used by 4 detail endpoints)
  - Unified `discover_movies`/`discover_shows` into shared `discover()` method
  - `TMDBAPIError` now stores `status_code` attribute for reliable error detection

- **Discovery Router Cleanup**
  - Added `_build_media_list()` helper (used by 4 endpoints)
  - Replaced `Optional[X]` imports with `X | None` syntax (Python 3.11+)

- **Settings Router Cleanup**
  - Extracted `_test_arr_connection()` helper for Radarr/Sonarr connection tests

- **Centralized Client Factories**
  - Library router imports `get_radarr_client`/`get_sonarr_client` from their modules instead of redefining

### Fixed

- **WatchlistView** sent `'tv'` media type to batch process endpoint; schema expects `'show'`
- **`datetime.utcnow`** replaced with timezone-aware `datetime.now(timezone.utc)` (deprecated in Python 3.12+)

### Removed

- Unused `isInLibrary` computed property in StatusBadge component
- Unused library service functions (`getMovieStatus`, `addMovie`, `addShow`, `getShowStatus`, `getRadarrQueue`, `getSonarrQueue`, `getRecentMovies`, `getRecentShows`)
- Dead code in appStore (Pinia store actions that were never imported)

---

## [2.4.1] - 2026-01-31

### Fixed

- **Database Schema Migration**
  - Added missing `is_season_update` column to watchlist table
  - Fixed 500 error on watchlist page load
  - Fixed inability to add shows to watchlist

---

## [2.4.0] - 2026-01-30

### Added

- **Library Status Filter**
  - New filter in FilterPanel: "All", "In Library", "Not in Library"
  - DiscoverView filters results by Radarr/Sonarr library status
  - Easily find content you don't already have

- **Season Update Indicator**
  - WatchlistView shows "+Seasons" badge for items that are season updates
  - Distinguishes between new shows and adding seasons to existing shows

- **Season Status for Existing Shows**
  - MediaDetailView fetches season status from Sonarr for shows already in library
  - SeasonSelectModal shows which seasons are downloaded (green), monitored (yellow), or available
  - Add more seasons to shows already in your library

---

## [2.3.0] - 2026-01-30

### Added

- **Root Folder Configuration**
  - Configure custom root folder paths for Radarr and Sonarr in Settings UI
  - New fields: `radarr_root_folder` and `sonarr_root_folder`
  - Allows directing content to specific storage locations (e.g., `/movies-usb`, `/tv-usb`)
  - Falls back to default root folder if not specified

### Changed

- Added `cloudflare_tunnel_token` to config to support Docker deployment .env files

---

## [2.2.0] - 2026-01-30

### Added

- **Docker Deployment**
  - Dockerfile for backend (Python 3.11, FastAPI, uvicorn)
  - Dockerfile for frontend (Node build + nginx)
  - docker-compose.yml with three services: backend, frontend, cloudflared
  - nginx.conf for reverse proxy to backend API
  - .dockerignore to exclude unnecessary files from builds

- **Cloudflare Tunnel Integration**
  - Secure remote access without port forwarding
  - CLOUDFLARE_TUNNEL_TOKEN environment variable
  - Auto-restart on NAS reboot

- **NAS Deployment Documentation**
  - Step-by-step Synology deployment guide in README
  - Docker commands reference table
  - Architecture diagram

### Changed

- Added `cryptography` dependency for settings encryption in Docker builds

---

## [2.1.0] - 2026-01-30

### Added

- **Season Selection for TV Shows**
  - Select specific seasons when adding TV shows to watchlist
  - SeasonSelectModal opens automatically for TV shows
  - Expandable rows in WatchlistView to edit seasons
  - "X of Y seasons" summary display
  - Selected seasons passed to Sonarr when processing

- **Watchlist Season API**
  - `PATCH /api/watchlist/{tmdb_id}/seasons` - Update selected seasons
  - `selected_seasons` field in watchlist add/list endpoints
  - `total_seasons` included in watchlist item responses

- **Sonarr Season Monitoring**
  - Per-season monitoring based on user selection
  - Season 0 (specials) never auto-monitored
  - Backward compatible (null = all seasons)

### Changed

- TV shows now open season selector modal instead of adding directly
- WatchlistView shows expandable season editor for TV shows
- API timeout increased to 30 seconds

### Fixed

- Library and queue API calls now run in parallel for faster response
- Settings connection test uses correct setting lookup
- Discover page now shows watchlist status for items
- Batch process API now accepts 'show' media type (was incorrectly expecting 'tv')
- Discover page now shows season selector when adding TV shows (was adding all seasons)

---

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
