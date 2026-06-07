# Movie Discovery App

> **Standard install = NAS Docker.** The canonical deployment of this app is the Dockerized `hoveyflix` stack on the Synology NAS (behind a Cloudflare tunnel), **not** local dev. **When the user says "rebuild", it means: deploy to the NAS** via the [Docker Deployment](#docker-deployment) steps below (ship `git archive HEAD` → `docker-compose up -d --build`). Go straight to it — do not ask which target, and do not rebuild a local Docker stack.

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
git archive --format=tar HEAD | ssh "Troy Hovey@192.168.1.104" "tar -xf - -C /volume1/docker/hoveyflix"

# On the NAS — docker works without sudo; DOCKER_BUILDKIT=0 avoids the buildx
# permission error on the root-owned ~/.docker/buildx:
ssh "Troy Hovey@192.168.1.104" "cd /volume1/docker/hoveyflix && DOCKER_BUILDKIT=0 COMPOSE_DOCKER_CLI_BUILD=0 /usr/local/bin/docker-compose up -d --build"
```

## Project Structure

```
backend/src/app/
├── modules/
│   ├── arr_base.py   # BaseArrClient: shared HTTP client for Radarr/Sonarr
│   ├── discovery/    # TMDB: trending, search, filters, details, person, collection
│   ├── watchlist/    # CRUD, batch process, batch delete, season selection, details (priority/notes/tags)
│   ├── radarr/       # Movie library: status, add, queue, recent (extends BaseArrClient)
│   ├── sonarr/       # TV library: status, add, queue, recent, season monitoring (extends BaseArrClient)
│   ├── settings/     # API keys, root folder paths, default quality profiles, streaming_region (region for streaming-availability lookups, default US) (encrypted keys; rest plain)
│   ├── library/      # Combined activity feed
│   ├── calendar/      # Coming-Soon agenda: Radarr/Sonarr calendars + watchlist release dates
│   └── recommendations/ # For You: aggregate TMDB recommendations (watchlist + owned library seeds), in-process TTL cache
├── config.py         # Loads .env from project root
├── models.py         # SQLAlchemy: Settings, Watchlist (selected_seasons, priority, tags), MediaCache
└── main.py           # FastAPI app

frontend/src/
├── views/            # DiscoverView, WatchlistView, LibraryView, SettingsView,
│                     # MediaDetailView, PersonView, CollectionView, CalendarView, ForYouView
├── components/       # FilterPanel, PaginationControls, TrailerModal, CastCarousel,
│                     # MediaCarousel, MediaCard, QueueItem, DownloadProgress,
│                     # StatusBadge, SeasonSelectModal, WatchProviders
├── services/         # api.js, discover.js, watchlist.js, library.js, settings.js, sonarr.js, calendar.js, forYou.js
├── utils/            # discoverState.js (URL-as-state for Discover; unit-tested),
│                     # watchlistState.js (URL-as-state + sort/filter + priority grouping + tags helpers for Watchlist; unit-tested),
│                     # calendarState.js (agenda grouping/formatting; unit-tested),
│                     # forYouState.js (For You add-target routing: movie→watchlist, show→detail; unit-tested)
└── router/           # Vue Router config
```

## Key Files

| File | Purpose |
|------|---------|
| `backend/src/app/modules/arr_base.py` | BaseArrClient: persistent httpx client, `_get`/`_post`/`_put` |
| `backend/src/app/modules/discovery/tmdb_client.py` | All TMDB API calls (`_get_or_none` for 404 handling) |
| `backend/src/app/modules/watchlist/router.py` | `_enrich_watchlist_item()`, `_parse_seasons()`, `_parse_tags()` / `update_details` shared helpers |
| `backend/src/app/modules/watchlist/service.py` | Watchlist CRUD + parallel batch processing |
| `backend/src/app/modules/sonarr/client.py` | Sonarr API with season monitoring |
| `frontend/src/components/SeasonSelectModal.vue` | TV show season picker (with status display) |
| `frontend/src/views/WatchlistView.vue` | Expandable season editing |
| `backend/src/app/modules/calendar/service.py` | Pure agenda normalizer (Sonarr/Radarr/watchlist -> unified sorted entries) |
| `backend/src/app/modules/recommendations/service.py` | Pure For You seed/exclusion/aggregation (frequency→vote→popularity ranking) |

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
- **Additive DB migrations** — `init_db()` runs `_migrate_watchlist_columns()` (guarded, idempotent `ALTER TABLE ... ADD COLUMN`) **after** `create_all`. `create_all` only creates missing tables; it never adds columns to an existing one, so **any new column on an existing model MUST get a guarded additive migration here** — otherwise the live NAS SQLite DB 500s with "no such column" (the v2.4.1 incident).

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
