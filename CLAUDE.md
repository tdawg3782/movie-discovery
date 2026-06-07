# Movie Discovery App

## Commands

| Command | Description |
|---------|-------------|
| `start.bat` | Start backend + frontend (local dev) |
| `stop.bat` | Stop all servers |
| `cd backend && pytest -v` | Run tests |
| `cd backend && pytest --cov=app` | Tests with coverage |
| `cd frontend && npm run test` | Run frontend unit tests (Vitest) |

## Docker Deployment

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Orchestrates backend, frontend, cloudflared |
| `backend/Dockerfile` | Python 3.11 + FastAPI |
| `frontend/Dockerfile` | Node build + nginx |
| `frontend/nginx.conf` | Reverse proxy /api to backend |

Deploy to the NAS. The NAS has **no `git`** and Docker is **not on the login PATH**, so
ship the committed tree from a machine that has git, then build with the **legacy** builder
(buildx is broken on the box). `git archive` ships only tracked files, so the NAS's `.env`
and `data/` (the SQLite DB) are left untouched:
```bash
# From the repo root on a machine with git:
git archive --format=tar HEAD | ssh user@nas-ip "tar -xf - -C /volume1/docker/hoveyflix"

# On the NAS — docker works without sudo; DOCKER_BUILDKIT=0 avoids the buildx
# permission error on the root-owned ~/.docker/buildx:
ssh user@nas-ip "cd /volume1/docker/hoveyflix && DOCKER_BUILDKIT=0 /usr/local/bin/docker-compose up -d --build"
```

## Project Structure

```
backend/src/app/
├── modules/
│   ├── arr_base.py   # BaseArrClient: shared HTTP client for Radarr/Sonarr
│   ├── discovery/    # TMDB: trending, search, filters, details, person, collection
│   ├── watchlist/    # CRUD, batch process, batch delete, season selection
│   ├── radarr/       # Movie library: status, add, queue, recent (extends BaseArrClient)
│   ├── sonarr/       # TV library: status, add, queue, recent, season monitoring (extends BaseArrClient)
│   ├── settings/     # API keys, root folder paths, default quality profiles (encrypted keys; rest plain)
│   └── library/      # Combined activity feed
├── config.py         # Loads .env from project root
├── models.py         # SQLAlchemy: Settings, Watchlist (with selected_seasons), MediaCache
└── main.py           # FastAPI app

frontend/src/
├── views/            # DiscoverView, WatchlistView, LibraryView, SettingsView,
│                     # MediaDetailView, PersonView, CollectionView
├── components/       # FilterPanel, PaginationControls, TrailerModal, CastCarousel,
│                     # MediaCarousel, MediaCard, QueueItem, DownloadProgress,
│                     # StatusBadge, SeasonSelectModal
├── services/         # api.js, discover.js, watchlist.js, library.js, settings.js, sonarr.js
├── utils/            # discoverState.js (URL-as-state for Discover; unit-tested)
└── router/           # Vue Router config
```

## Key Files

| File | Purpose |
|------|---------|
| `backend/src/app/modules/arr_base.py` | BaseArrClient: persistent httpx client, `_get`/`_post`/`_put` |
| `backend/src/app/modules/discovery/tmdb_client.py` | All TMDB API calls (`_get_or_none` for 404 handling) |
| `backend/src/app/modules/watchlist/router.py` | `_enrich_watchlist_item()`, `_parse_seasons()` shared helpers |
| `backend/src/app/modules/watchlist/service.py` | Watchlist CRUD + parallel batch processing |
| `backend/src/app/modules/sonarr/client.py` | Sonarr API with season monitoring |
| `frontend/src/components/SeasonSelectModal.vue` | TV show season picker (with status display) |
| `frontend/src/views/WatchlistView.vue` | Expandable season editing |

## Code Style

**Backend (Python):**
- Type hints on all functions
- Async/await for I/O
- Pydantic for schemas
- HTTPException for errors

**Frontend (Vue):**
- Composition API with `<script setup>`
- Services auto-unwrap `response.data`

## Architecture Patterns

- **BaseArrClient** — Radarr/Sonarr clients inherit shared HTTP logic with persistent connection reuse
- **TMDBClient._get_or_none()** — Returns None on 404 instead of raising (used for detail endpoints)
- **Watchlist enrichment** — `_enrich_watchlist_item()` in router handles TMDB metadata + fallbacks
- **Batch processing** — `asyncio.gather()` (backend) and `Promise.all()` (frontend) for parallelism
- **Client factories** — Defined once in each module's router, imported by library router
- **Media type convention** — App uses "show" internally, converts to "tv" for TMDB API calls

## Environment

IMPORTANT: `.env` must be in project root (not backend/).

```
TMDB_API_KEY=xxx
RADARR_URL=http://...
RADARR_API_KEY=xxx
SONARR_URL=http://...
SONARR_API_KEY=xxx
```

Settings can also be configured via UI at `/settings`.

## Workflow

1. **Add to Watchlist** - Click "+" on any poster (TV shows open season selector)
2. **Add More Seasons** - Click "+" on shows already in Sonarr to add new seasons (green=downloaded, yellow=monitored)
3. **Review in Watchlist** - Select items, expand TV shows to edit seasons ("+Seasons" shown for updates)
4. **Batch Process** - Send to Radarr/Sonarr (new shows added, existing shows get season monitoring updated)
5. **Filter Discovery** - Use "In Radarr/Sonarr" or "Not in Library" filters to find new content
6. **Monitor in Library** - See downloads and recent additions

## Testing

IMPORTANT: Run tests before committing backend changes:
```bash
cd backend && pytest -v
```
