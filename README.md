# Movie Discovery

A local movie and TV show discovery app with Sonarr/Radarr integration. Discover trending content, search for titles, and add them to your media server with one click.

## Features

- Browse trending movies and TV shows via TMDB
- Search for any movie or TV show
- See library status (available, downloading, added)
- One-click add to Sonarr (TV) or Radarr (Movies)
- Watchlist for saving items to review later
- Pagination with "Load More" for browsing
- Dark theme UI

## Screenshots

| Discover | Search |
|----------|--------|
| Browse trending content | Find any title |

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy, SQLite |
| Frontend | Vue 3, Vite, Pinia, Axios |
| APIs | TMDB (discovery), Sonarr (TV), Radarr (Movies) |

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Sonarr and/or Radarr running (local or network)
- [TMDB API key](https://www.themoviedb.org/settings/api)

### Installation

1. **Clone and configure:**
   ```bash
   git clone <repo-url>
   cd movie_discovery
   cp .env.example .env
   ```

2. **Edit `.env` with your settings:**
   ```
   TMDB_API_KEY=your_tmdb_api_key
   SONARR_URL=http://your-sonarr-ip:8989
   SONARR_API_KEY=your_sonarr_api_key
   RADARR_URL=http://your-radarr-ip:7878
   RADARR_API_KEY=your_radarr_api_key
   ```

3. **Install backend:**
   ```bash
   cd backend
   pip install -e ".[dev]"
   ```

4. **Install frontend:**
   ```bash
   cd frontend
   npm install
   ```

5. **Start the app:**
   ```bash
   # From project root
   start.bat
   ```

6. **Open** http://localhost:3000

### Manual Start

If you prefer to start servers manually:

```bash
# Terminal 1 - Backend
cd backend
uvicorn src.app.main:app --reload

# Terminal 2 - Frontend
cd frontend
npm run dev
```

## Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `TMDB_API_KEY` | TMDB API key for discovery | `abc123...` |
| `SONARR_URL` | Sonarr server URL | `http://192.168.1.100:8989` |
| `SONARR_API_KEY` | Sonarr API key | `xyz789...` |
| `RADARR_URL` | Radarr server URL | `http://192.168.1.100:7878` |
| `RADARR_API_KEY` | Radarr API key | `def456...` |
| `DATABASE_PATH` | SQLite database path | `./data/movie_discovery.db` |

### Getting API Keys

- **TMDB**: Create account at [themoviedb.org](https://www.themoviedb.org/), go to Settings > API
- **Sonarr**: Settings > General > Security > API Key
- **Radarr**: Settings > General > Security > API Key

## API Endpoints

### Discovery
- `GET /api/discover/movies/trending` - Trending movies
- `GET /api/discover/shows/trending` - Trending TV shows
- `GET /api/discover/search?q=query` - Search movies and shows

### Radarr (Movies)
- `GET /api/radarr/status/{tmdb_id}` - Check movie status
- `POST /api/radarr/add` - Add movie to Radarr

### Sonarr (TV Shows)
- `GET /api/sonarr/status/{tmdb_id}` - Check show status
- `POST /api/sonarr/add` - Add show to Sonarr

### Watchlist
- `GET /api/watchlist` - Get watchlist items
- `POST /api/watchlist` - Add to watchlist
- `DELETE /api/watchlist/{id}` - Remove from watchlist

### Health
- `GET /health` - API health check

## Development

### Running Tests

```bash
cd backend
pytest -v                    # Run all tests
pytest --cov=app             # With coverage
pytest tests/test_discovery_router.py -v  # Single module
```

### Project Structure

```
movie_discovery/
├── backend/
│   ├── src/app/
│   │   ├── modules/
│   │   │   ├── discovery/   # TMDB integration
│   │   │   ├── watchlist/   # Watchlist feature
│   │   │   ├── radarr/      # Radarr integration
│   │   │   └── sonarr/      # Sonarr integration
│   │   ├── config.py        # Environment settings
│   │   ├── database.py      # SQLite setup
│   │   ├── models.py        # SQLAlchemy models
│   │   ├── schemas.py       # Pydantic schemas
│   │   └── main.py          # FastAPI app
│   └── tests/               # Backend tests
├── frontend/
│   ├── src/
│   │   ├── views/           # Page components
│   │   ├── components/      # Reusable components
│   │   ├── services/        # API services
│   │   ├── stores/          # Pinia stores
│   │   └── router/          # Vue Router
│   └── vite.config.js       # Vite configuration
├── .env                     # Environment variables
├── .env.example             # Environment template
├── start.bat                # Start both servers
└── stop.bat                 # Stop both servers
```

## Troubleshooting

### "Internal Server Error" on trending/search
- Ensure `.env` is in the project root (not in `backend/`)
- Verify `TMDB_API_KEY` is set correctly

### "Radarr/Sonarr API error"
- Check URL is correct (include port)
- Verify API key from Settings > General
- Ensure Radarr/Sonarr is running

### Movie/show already exists
- The app now shows a clear message when a title is already in your library

### Frontend shows error but API works
- Clear browser cache and refresh
- Check browser console for specific errors

## License

MIT
