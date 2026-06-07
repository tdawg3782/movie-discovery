# Movie Discovery

A local movie and TV show discovery app with Radarr/Sonarr integration. Browse, filter, and add content to your media server.

## Features

| Feature | Description |
|---------|-------------|
| **Discovery** | Browse trending movies and shows, filter by genre/year/rating |
| **Search** | Find any movie or TV show |
| **Detail Pages** | View trailers, cast, recommendations, collections |
| **Person Pages** | Browse actor/director filmographies |
| **Watchlist** | Stage items before adding to library (batch processing, season selection) |
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
3. Optionally set **Root Folder Paths** and a default **Quality Profile** for Radarr/Sonarr (e.g., `/movies-usb`, `/tv-usb`; leave a quality profile on "Use default" to keep the `*arr` auto profile)
4. Click **Test** to verify each connection
5. Click **Save**

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
3. Page through results with **Prev / Next** (each page replaces the current results)
4. Click any poster to view details
5. Click **+** to add to your watchlist (TV shows prompt for season selection)

Your active tab, page, search, and filters are saved in the page URL, so reloading or using the browser **Back** button (for example, returning from a detail page) takes you back to exactly where you were.

### Adding to Library

1. Go to **Watchlist**
2. For TV shows: click row to expand and select specific seasons
3. Select items with checkboxes
4. Click **Add to Library**
5. Confirm in the modal (selected seasons sent to Sonarr)

### Monitoring Downloads

1. Go to **Library**
2. **Downloads** tab shows active queue with progress
3. **Recently Added** tab shows completed items
4. Toggle **Auto-refresh** for live updates

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11, FastAPI, SQLAlchemy, SQLite, httpx |
| Frontend | Vue 3, Vite, Axios |
| APIs | TMDB, Radarr, Sonarr |

## Project Structure

```
movie_discovery/
├── backend/src/app/
│   ├── modules/
│   │   ├── arr_base.py   # Shared HTTP client for Radarr/Sonarr
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
| GET | `/api/watchlist` | List items (includes season info) |
| POST | `/api/watchlist` | Add item (with optional selected_seasons) |
| DELETE | `/api/watchlist/{id}` | Remove item |
| PATCH | `/api/watchlist/{tmdb_id}/seasons` | Update selected seasons |
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
| GET | `/api/radarr/quality-profiles` | List Radarr quality profiles |
| GET | `/api/sonarr/quality-profiles` | List Sonarr quality profiles |

## Docker Deployment (Synology NAS)

Deploy to a Synology NAS with remote access via Cloudflare Tunnel.

### Prerequisites

- Synology NAS with Container Manager or Docker
- Domain name (for Cloudflare Tunnel)
- Cloudflare account (free tier works)

### Setup

1. **Create Cloudflare Tunnel**
   - Go to [Cloudflare Zero Trust](https://one.dash.cloudflare.com/) → Networks → Tunnels
   - Create tunnel, copy the token
   - Configure public hostname pointing to `frontend:80`

2. **Create the stack directory on the NAS** (it has no `git`, so the code is shipped from
   your machine in step 4)
   ```bash
   ssh user@nas-ip "mkdir -p /volume1/docker/hoveyflix"
   # copy the env template over, then fill it in (next step):
   scp .env.example "user@nas-ip:/volume1/docker/hoveyflix/.env"
   ```

3. **Configure environment**
   ```bash
   # .env on NAS
   TMDB_API_KEY=your_key
   RADARR_URL=http://192.168.x.x:7878    # Use NAS IP, not localhost
   RADARR_API_KEY=your_key
   SONARR_URL=http://192.168.x.x:8989
   SONARR_API_KEY=your_key
   CLOUDFLARE_TUNNEL_TOKEN=eyJ...
   ```

4. **Ship the code and build** from a machine with git. `git archive` sends only tracked
   files, so the NAS's `.env` and `data/` stay untouched; `DOCKER_BUILDKIT=0` is required
   (the box's buildx is broken) and Docker runs without sudo:
   ```bash
   git archive --format=tar HEAD | ssh user@nas-ip "tar -xf - -C /volume1/docker/hoveyflix"
   ssh user@nas-ip "cd /volume1/docker/hoveyflix && DOCKER_BUILDKIT=0 /usr/local/bin/docker-compose up -d --build"
   ```

5. **Verify**
   - Check tunnel status in Cloudflare dashboard
   - Visit your domain (e.g., `movies.yourdomain.com`)

### Docker Commands

Run these in `/volume1/docker/hoveyflix` on the NAS (Docker needs no sudo; use full
`/usr/local/bin` paths — they're not on the login PATH):

| Task | Command |
|------|---------|
| Start | `/usr/local/bin/docker-compose up -d` |
| Stop | `/usr/local/bin/docker-compose down` |
| Rebuild | `DOCKER_BUILDKIT=0 /usr/local/bin/docker-compose up -d --build` |
| View logs | `/usr/local/bin/docker logs hoveyflix-backend` |
| Restart | `/usr/local/bin/docker-compose restart` |
| Update | from your machine: `git archive --format=tar HEAD \| ssh user@nas-ip "tar -xf - -C /volume1/docker/hoveyflix"`, then Rebuild |

### Architecture

```
Internet → Cloudflare → Tunnel → frontend:80 (nginx)
                                      ↓
                               backend:8000 (FastAPI)
                                      ↓
                            Radarr/Sonarr (local network)
```

## Development

### Running Tests

**Backend:**
```bash
cd backend
pytest -v              # All tests
pytest --cov=app       # With coverage
```

**Frontend** (Vitest unit tests, added in v2.7.0):
```bash
cd frontend
npm run test
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
