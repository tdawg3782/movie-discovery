# Movie Discovery App

## Commands

| Command | Description |
|---------|-------------|
| `start.bat` | Start backend + frontend (local dev) |
| `stop.bat` | Stop all servers |
| `cd backend && pytest -v` | Run tests |
| `cd backend && pytest --cov=app` | Tests with coverage |

## Docker Deployment

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Orchestrates backend, frontend, cloudflared |
| `backend/Dockerfile` | Python 3.11 + FastAPI |
| `frontend/Dockerfile` | Node build + nginx |
| `frontend/nginx.conf` | Reverse proxy /api to backend |

Deploy to NAS:
```bash
cd /volume1/docker/hoveyflix
sudo docker-compose up -d --build
```

## Project Structure

```
backend/src/app/
├── modules/
│   ├── discovery/    # TMDB: trending, search, filters, details, person, collection
│   ├── watchlist/    # CRUD, batch process, batch delete, season selection
│   ├── radarr/       # Movie library: status, add, queue, recent
│   ├── sonarr/       # TV library: status, add, queue, recent, season monitoring
│   ├── settings/     # API keys, root folder paths (encrypted storage)
│   └── library/      # Combined activity feed
├── config.py         # Loads .env from project root
├── models.py         # SQLAlchemy: Settings, Watchlist (with selected_seasons), MediaCache
└── main.py           # FastAPI app

frontend/src/
├── views/            # DiscoverView, WatchlistView, LibraryView, SettingsView,
│                     # MediaDetailView, PersonView, CollectionView
├── components/       # FilterPanel, TrailerModal, CastCarousel, MediaCarousel,
│                     # QueueItem, DownloadProgress, StatusBadge, SeasonSelectModal
├── services/         # api.js, discover.js, watchlist.js, library.js, settings.js
└── router/           # Vue Router config
```

## Key Files

| File | Purpose |
|------|---------|
| `backend/src/app/modules/discovery/tmdb_client.py` | All TMDB API calls |
| `backend/src/app/modules/watchlist/service.py` | Watchlist CRUD + season storage |
| `backend/src/app/modules/sonarr/client.py` | Sonarr API with season monitoring |
| `frontend/src/components/SeasonSelectModal.vue` | TV show season picker |
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
2. **Review in Watchlist** - Select items, expand TV shows to edit seasons
3. **Batch Process** - Send to Radarr/Sonarr with season selection
4. **Monitor in Library** - See downloads and recent additions

## Testing

IMPORTANT: Run tests before committing backend changes:
```bash
cd backend && pytest -v
```
