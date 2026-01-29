# Movie Discovery App

## Commands

| Command | Description |
|---------|-------------|
| `start.bat` | Start backend + frontend |
| `stop.bat` | Stop all servers |
| `cd backend && pytest -v` | Run tests |
| `cd backend && pytest --cov=app` | Tests with coverage |

## Project Structure

```
backend/src/app/
├── modules/
│   ├── discovery/    # TMDB: trending, search, filters, details, person, collection
│   ├── watchlist/    # CRUD, batch process, batch delete
│   ├── radarr/       # Movie library: status, add, queue, recent
│   ├── sonarr/       # TV library: status, add, queue, recent
│   ├── settings/     # API key management (encrypted storage)
│   └── library/      # Combined activity feed
├── config.py         # Loads .env from project root
├── models.py         # SQLAlchemy: Settings, Watchlist, MediaCache
└── main.py           # FastAPI app

frontend/src/
├── views/            # DiscoverView, WatchlistView, LibraryView, SettingsView,
│                     # MediaDetailView, PersonView, CollectionView
├── components/       # FilterPanel, TrailerModal, CastCarousel, MediaCarousel,
│                     # QueueItem, DownloadProgress, StatusBadge
├── services/         # api.js, discover.js, watchlist.js, library.js, settings.js
└── router/           # Vue Router config
```

## Key Files

| File | Purpose |
|------|---------|
| `backend/src/app/modules/discovery/tmdb_client.py` | All TMDB API calls |
| `backend/src/app/modules/discovery/router.py` | Discovery + detail endpoints |
| `backend/src/app/modules/settings/service.py` | Encrypted settings storage |
| `frontend/src/views/DiscoverView.vue` | Main page with filters |
| `frontend/src/components/FilterPanel.vue` | Genre/year/rating filters |

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

## Routes

| Path | View |
|------|------|
| `/` | DiscoverView (trending + filters) |
| `/watchlist` | WatchlistView (staging queue) |
| `/library` | LibraryView (recent + downloads) |
| `/settings` | SettingsView (API keys) |
| `/movie/:id` | MediaDetailView |
| `/tv/:id` | MediaDetailView |
| `/person/:id` | PersonView |
| `/collection/:id` | CollectionView |

## Workflow

1. **Add to Watchlist** - Click "+" on any poster
2. **Review in Watchlist** - Select items, batch process
3. **Monitor in Library** - See downloads and recent additions

## Testing

Run tests before committing backend changes:
```bash
cd backend && pytest -v
```
