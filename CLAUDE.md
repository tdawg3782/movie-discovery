# Movie Discovery App

## Bash Commands

| Command | Description |
|---------|-------------|
| `start.bat` | Start both backend and frontend servers |
| `stop.bat` | Stop all running servers |
| `cd backend && uvicorn src.app.main:app --reload` | Start backend only |
| `cd frontend && npm run dev` | Start frontend only |
| `cd backend && pytest -v` | Run backend tests |
| `cd backend && pytest --cov=app` | Run tests with coverage |

## Project Structure

```
movie_discovery/
├── backend/           # FastAPI Python backend
│   └── src/app/
│       ├── modules/   # Feature modules (discovery, watchlist, radarr, sonarr)
│       ├── config.py  # Environment settings (loads from root .env)
│       └── main.py    # FastAPI app entry point
├── frontend/          # Vue 3 + Vite frontend
│   └── src/
│       ├── views/     # Page components
│       ├── services/  # API service layer
│       └── stores/    # Pinia stores
└── .env               # Environment variables (IMPORTANT: at project root)
```

## Key Files

- `backend/src/app/config.py` - Settings via pydantic-settings, loads `.env` from project root
- `backend/src/app/modules/*/client.py` - API clients (TMDB, Radarr, Sonarr)
- `backend/src/app/modules/*/router.py` - FastAPI route handlers
- `frontend/src/services/api.js` - Axios instance (auto-unwraps response.data)
- `frontend/src/views/DiscoverView.vue` - Main discovery page with search

## Code Style

### Backend (Python)
- Type hints on all functions
- Async/await for all I/O operations
- Pydantic models for request/response schemas
- HTTPException for API errors with meaningful messages

### Frontend (Vue/JavaScript)
- Composition API with `<script setup>`
- Services return unwrapped data (axios interceptor handles `.data`)
- Pinia for state management

## Environment Variables

IMPORTANT: The `.env` file MUST be in the project root (not in backend/).

```
TMDB_API_KEY=xxx          # Required for discovery
SONARR_URL=http://...     # Sonarr server URL
SONARR_API_KEY=xxx        # Sonarr API key
RADARR_URL=http://...     # Radarr server URL
RADARR_API_KEY=xxx        # Radarr API key
DATABASE_PATH=./data/...  # SQLite database path
```

## Common Issues

### "Internal Server Error" on discovery endpoints
- Check if `.env` is in project root (not backend/)
- Verify TMDB_API_KEY is set correctly

### "Radarr/Sonarr API error: 400"
- Quality profile auto-detected from first available profile
- Check if movie/show already exists in library (returns clear error message)

### Frontend shows "Failed to load" but API works
- Services auto-unwrap `response.data` - access `response.results` not `response.data.results`

## Testing

- Backend: 75 tests covering all modules
- Run single module: `pytest tests/test_discovery_router.py -v`
- MUST run tests before committing changes to backend
