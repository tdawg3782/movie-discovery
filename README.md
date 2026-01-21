# Movie Discovery

A local movie and TV show discovery app with Sonarr/Radarr integration.

## Features

- Browse trending movies and TV shows via TMDB
- Search for specific titles
- See what's already in your library
- One-click add to Sonarr/Radarr
- Watchlist for saving items to review later

## Tech Stack

- **Backend:** Python, FastAPI, SQLite
- **Frontend:** Vue 3, Vite, Pinia
- **APIs:** TMDB, Sonarr, Radarr

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Sonarr and Radarr running locally
- TMDB API key

### Installation

1. Clone and configure:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

2. Backend:
   ```bash
   cd backend
   pip install -e ".[dev]"
   uvicorn app.main:app --reload
   ```

3. Frontend:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

4. Open http://localhost:5173

## Development

This project uses git worktrees for parallel development:

- `main` - Integration and shared code
- `feature/discovery-api` - TMDB integration
- `feature/sonarr-radarr` - Sonarr/Radarr modules
- `feature/watchlist` - Watchlist functionality
- `feature/frontend` - Vue UI components
