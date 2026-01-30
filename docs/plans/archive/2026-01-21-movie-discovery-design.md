# Movie Discovery App - Design Document

**Date:** 2026-01-21
**Status:** Approved

## Overview

A local movie and TV show discovery app that connects to Sonarr and Radarr for automated library management. Also serves as a learning project for parallel agent development using git worktrees.

## Goals

1. Discover movies and TV shows via TMDB API
2. Check library status against Sonarr/Radarr
3. One-click add to Sonarr/Radarr for downloading
4. Learn parallel agent workflows with git worktrees

## Technology Stack

| Component | Technology |
|-----------|------------|
| Frontend | Vue.js |
| Backend | Python + FastAPI |
| Database | SQLite |
| Discovery API | TMDB |
| Media Management | Sonarr (TV), Radarr (Movies) |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Vue.js Frontend                         │
│  (Discovery UI, Search, Watchlist, Library Status)          │
└─────────────────────┬───────────────────────────────────────┘
                      │ REST API
┌─────────────────────▼───────────────────────────────────────┐
│                  FastAPI Backend                            │
├─────────────┬─────────────┬─────────────┬──────────────────┤
│  Discovery  │  Watchlist  │   Sonarr    │     Radarr       │
│   Module    │   Module    │   Module    │     Module       │
└──────┬──────┴──────┬──────┴──────┬──────┴───────┬──────────┘
       │             │             │              │
       ▼             ▼             ▼              ▼
    TMDB API     SQLite DB    Sonarr API    Radarr API
```

### Backend Modules

1. **Discovery Module** - TMDB integration for trending, search, similar titles
2. **Watchlist Module** - CRUD for saved items to review later
3. **Sonarr Module** - TV show status checking and adding
4. **Radarr Module** - Movie status checking and adding

## API Endpoints

### Discovery
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/discover/movies/trending` | Trending movies from TMDB |
| GET | `/api/discover/shows/trending` | Trending TV shows from TMDB |
| GET | `/api/discover/search?q=...` | Search movies & shows |
| GET | `/api/discover/similar/{tmdb_id}` | Similar titles |

### Watchlist
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/watchlist` | List saved items |
| POST | `/api/watchlist` | Add item to watchlist |
| DELETE | `/api/watchlist/{id}` | Remove from watchlist |

### Sonarr
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/sonarr/status/{tvdb_id}` | Check show status |
| POST | `/api/sonarr/add` | Add show to Sonarr |

### Radarr
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/radarr/status/{tmdb_id}` | Check movie status |
| POST | `/api/radarr/add` | Add movie to Radarr |

## Database Schema

```sql
-- Cached metadata from TMDB (reduces API calls)
media_cache (
    id              INTEGER PRIMARY KEY,
    tmdb_id         INTEGER UNIQUE,
    media_type      TEXT,          -- 'movie' or 'show'
    title           TEXT,
    overview        TEXT,
    poster_path     TEXT,
    release_date    TEXT,
    vote_average    REAL,
    cached_at       TIMESTAMP
)

-- User's watchlist for items to review later
watchlist (
    id              INTEGER PRIMARY KEY,
    tmdb_id         INTEGER,
    media_type      TEXT,
    added_at        TIMESTAMP,
    notes           TEXT,          -- optional user notes
    UNIQUE(tmdb_id, media_type)
)

-- Track what's been added to Sonarr/Radarr (avoids re-checking)
library_status (
    id              INTEGER PRIMARY KEY,
    tmdb_id         INTEGER,
    media_type      TEXT,
    status          TEXT,          -- 'added', 'downloading', 'available'
    checked_at      TIMESTAMP,
    UNIQUE(tmdb_id, media_type)
)
```

## Frontend Structure

```
src/
├── views/
│   ├── DiscoverView.vue      # Trending & browse page
│   ├── SearchView.vue        # Search results
│   ├── WatchlistView.vue     # Saved items to review
│   └── DetailView.vue        # Single movie/show details
├── components/
│   ├── MediaCard.vue         # Poster + title + quick actions
│   ├── MediaGrid.vue         # Grid of MediaCards
│   ├── StatusBadge.vue       # "In Library" / "Downloading" / "Add"
│   └── AddModal.vue          # Confirm add to Sonarr/Radarr
├── services/
│   ├── api.js                # Axios wrapper for backend
│   ├── discover.js           # Discovery API calls
│   ├── watchlist.js          # Watchlist API calls
│   └── library.js            # Sonarr/Radarr status calls
└── stores/
    └── appStore.js           # Pinia store for state
```

## Parallel Development Strategy

### Git Worktrees

| Worktree | Focus | Dependencies |
|----------|-------|--------------|
| `main` | Project setup, integration | None |
| `feature/discovery-api` | TMDB integration, discovery endpoints | API contract |
| `feature/sonarr-radarr` | Sonarr/Radarr modules | API contract |
| `feature/watchlist` | Watchlist CRUD, SQLite | API contract |
| `feature/frontend` | Vue app, all UI components | API contract |

### Workflow

1. Define API contracts in `main`
2. Create worktrees for each feature branch
3. Agents work in parallel on independent modules
4. Merge completed features back to `main`

## Error Handling

| Layer | Strategy |
|-------|----------|
| TMDB API | Retry with backoff, cache fallback |
| Sonarr/Radarr | Connection test on startup, clear error messages |
| SQLite | Minimal - local file |
| Frontend | Toast notifications, loading states |

## Testing Strategy

| Module | Approach |
|--------|----------|
| Discovery | Mock TMDB responses |
| Sonarr/Radarr | Mock API responses |
| Watchlist | SQLite in-memory |
| Frontend | Component tests + E2E for critical flows |

## Configuration

```yaml
# config.yaml
tmdb:
  api_key: "your-tmdb-api-key"

sonarr:
  url: "http://localhost:8989"
  api_key: "your-sonarr-api-key"

radarr:
  url: "http://localhost:7878"
  api_key: "your-radarr-api-key"

database:
  path: "./data/movie_discovery.db"
```

## V1 Scope

**Included:**
- TMDB trending, search, similar titles
- Watchlist for saving items to review
- Add movies to Radarr
- Add TV shows to Sonarr
- Check library status (owned/downloading)

**Excluded (future):**
- Personal recommendations based on watch history
- Plex/Jellyfin integration
- Full Sonarr/Radarr management (edit, delete)
- Multiple user profiles
