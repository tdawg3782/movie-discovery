# Movie Discovery

A local movie and TV show discovery app with Radarr/Sonarr integration. Browse, filter, and add content to your media server.

## Features

| Feature | Description |
|---------|-------------|
| **Discovery** | Browse trending movies and shows, filter by genre/year/rating |
| **Search** | Find any movie or TV show |
| **Detail Pages** | View trailers, cast, recommendations, collections |
| **Person Pages** | Browse actor/director filmographies |
| **Watchlist** | Stage items before adding to library (batch processing) |
| **Library Monitor** | See recent additions and download progress |
| **Settings** | Configure API keys via UI |

## Navigation

```
Discover → Watchlist → Library → Settings
    ↓
  [poster click]
    ↓
Detail Page → Person Page → Collection Page
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- [TMDB API key](https://www.themoviedb.org/settings/api)
- Sonarr and/or Radarr (optional, for library integration)

### Installation

```bash
git clone <repo-url>
cd movie_discovery

# Backend
cd backend
pip install -e ".[dev]"

# Frontend
cd ../frontend
npm install

# Start
cd ..
start.bat
```

Open http://localhost:3000

### First-Time Setup

1. Go to **Settings** (`/settings`)
2. Enter your API keys (TMDB required, Radarr/Sonarr optional)
3. Click **Test** to verify each connection
4. Click **Save**

Alternatively, create `.env` in the project root:

```
TMDB_API_KEY=your_key
RADARR_URL=http://localhost:7878
RADARR_API_KEY=your_key
SONARR_URL=http://localhost:8989
SONARR_API_KEY=your_key
```

## Usage

### Discovering Content

1. Browse trending on the **Discover** page
2. Use **Filters** to narrow by genre, year, rating
3. Click any poster to view details
4. Click **+** to add to your watchlist

### Adding to Library

1. Go to **Watchlist**
2. Select items with checkboxes
3. Click **Add to Library**
4. Confirm in the modal

### Monitoring Downloads

1. Go to **Library**
2. **Downloads** tab shows active queue with progress
3. **Recently Added** tab shows completed items
4. Toggle **Auto-refresh** for live updates

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11, FastAPI, SQLAlchemy, SQLite |
| Frontend | Vue 3, Vite, Pinia, Axios |
| APIs | TMDB, Radarr, Sonarr |

## Project Structure

```
movie_discovery/
├── backend/src/app/
│   ├── modules/
│   │   ├── discovery/    # TMDB: trending, search, filters, details
│   │   ├── watchlist/    # Watchlist CRUD, batch processing
│   │   ├── radarr/       # Movies: status, add, queue, recent
│   │   ├── sonarr/       # TV: status, add, queue, recent
│   │   ├── settings/     # API key management
│   │   └── library/      # Combined activity feed
│   ├── config.py
│   ├── models.py
│   └── main.py
├── frontend/src/
│   ├── views/
│   │   ├── DiscoverView.vue
│   │   ├── WatchlistView.vue
│   │   ├── LibraryView.vue
│   │   ├── SettingsView.vue
│   │   ├── MediaDetailView.vue
│   │   ├── PersonView.vue
│   │   └── CollectionView.vue
│   ├── components/
│   │   ├── FilterPanel.vue
│   │   ├── TrailerModal.vue
│   │   ├── CastCarousel.vue
│   │   └── ...
│   └── services/
├── start.bat
└── stop.bat
```

## API Endpoints

### Discovery
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/discover/movies/trending` | Trending movies |
| GET | `/api/discover/shows/trending` | Trending shows |
| GET | `/api/discover/movies?genre=28&year=2024` | Filtered movies |
| GET | `/api/discover/shows?genre=18&rating_gte=8` | Filtered shows |
| GET | `/api/discover/search?q=query` | Search |
| GET | `/api/discover/movies/{id}` | Movie details |
| GET | `/api/discover/shows/{id}` | Show details |
| GET | `/api/discover/person/{id}` | Person details |
| GET | `/api/discover/collection/{id}` | Collection |
| GET | `/api/genres/movies` | Movie genres |
| GET | `/api/genres/shows` | TV genres |

### Watchlist
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/watchlist` | List items |
| POST | `/api/watchlist` | Add item |
| DELETE | `/api/watchlist/{id}` | Remove item |
| POST | `/api/watchlist/process` | Batch add to library |
| DELETE | `/api/watchlist/batch` | Batch delete |

### Library
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/library/activity` | Recent additions |
| GET | `/api/library/queue` | Download queue |
| GET | `/api/radarr/queue` | Movie queue |
| GET | `/api/radarr/recent` | Recent movies |
| GET | `/api/sonarr/queue` | TV queue |
| GET | `/api/sonarr/recent` | Recent shows |

### Settings
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/settings` | Get settings (keys masked) |
| PUT | `/api/settings` | Update settings |
| POST | `/api/settings/test` | Test connection |

## Development

### Running Tests

```bash
cd backend
pytest -v              # All tests
pytest --cov=app       # With coverage
```

### Manual Server Start

```bash
# Terminal 1
cd backend && uvicorn src.app.main:app --reload

# Terminal 2
cd frontend && npm run dev
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Internal Server Error" on discovery | Check TMDB_API_KEY in Settings or .env |
| "Radarr/Sonarr API error" | Verify URL and API key in Settings |
| Filters not working | Clear filters and try again |
| Trailer not playing | Some titles don't have trailers on TMDB |

## License

MIT
