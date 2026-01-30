# Movie Discovery App - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a movie/TV discovery app with Vue frontend, FastAPI backend, and Sonarr/Radarr integration.

**Architecture:** Four independent backend modules (discovery, watchlist, sonarr, radarr) behind a FastAPI server, with a Vue.js SPA frontend. SQLite for persistence. Designed for parallel agent development via git worktrees.

**Tech Stack:** Python 3.11+, FastAPI, SQLite, Vue 3, Vite, Pinia, Axios

---

## Phase 0: Project Setup (main branch)

> Execute in: `movie_discovery/` (main workspace)

### Task 0.1: Create Python Project Structure

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/src/app/__init__.py`
- Create: `backend/src/app/main.py`
- Create: `backend/src/app/config.py`

**Step 1: Create backend directory structure**

```bash
mkdir -p backend/src/app/modules
mkdir -p backend/tests
```

**Step 2: Create pyproject.toml**

```toml
[project]
name = "movie-discovery"
version = "0.1.0"
description = "Movie and TV show discovery with Sonarr/Radarr integration"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "httpx>=0.26.0",
    "sqlalchemy>=2.0.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.1.0",
]

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py311"
```

**Step 3: Create config.py**

```python
"""Application configuration via environment variables."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # TMDB
    tmdb_api_key: str = ""
    tmdb_base_url: str = "https://api.themoviedb.org/3"

    # Sonarr
    sonarr_url: str = "http://localhost:8989"
    sonarr_api_key: str = ""

    # Radarr
    radarr_url: str = "http://localhost:7878"
    radarr_api_key: str = ""

    # Database
    database_path: str = "./data/movie_discovery.db"

    class Config:
        env_file = ".env"


settings = Settings()
```

**Step 4: Create main.py (FastAPI app shell)**

```python
"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Movie Discovery API",
    description="Discover movies and TV shows, integrate with Sonarr/Radarr",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
```

**Step 5: Create __init__.py**

```python
"""Movie Discovery API."""
```

**Step 6: Commit**

```bash
git add backend/
git commit -m "feat: initialize FastAPI backend structure

- Add pyproject.toml with dependencies
- Create config module with pydantic-settings
- Set up FastAPI app with CORS middleware
- Add health check endpoint

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 0.2: Create Database Schema

**Files:**
- Create: `backend/src/app/database.py`
- Create: `backend/src/app/models.py`

**Step 1: Create database.py**

```python
"""Database connection and session management."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""
    pass


engine = create_engine(
    f"sqlite:///{settings.database_path}",
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency that provides database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)
```

**Step 2: Create models.py**

```python
"""SQLAlchemy database models."""
from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MediaCache(Base):
    """Cached metadata from TMDB."""

    __tablename__ = "media_cache"

    id: Mapped[int] = mapped_column(primary_key=True)
    tmdb_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    media_type: Mapped[str] = mapped_column(String(10))  # 'movie' or 'show'
    title: Mapped[str] = mapped_column(String(255))
    overview: Mapped[str | None] = mapped_column(Text, nullable=True)
    poster_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    release_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    vote_average: Mapped[float | None] = mapped_column(Float, nullable=True)
    cached_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Watchlist(Base):
    """User's watchlist items."""

    __tablename__ = "watchlist"

    id: Mapped[int] = mapped_column(primary_key=True)
    tmdb_id: Mapped[int] = mapped_column(Integer, index=True)
    media_type: Mapped[str] = mapped_column(String(10))
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )


class LibraryStatus(Base):
    """Track items added to Sonarr/Radarr."""

    __tablename__ = "library_status"

    id: Mapped[int] = mapped_column(primary_key=True)
    tmdb_id: Mapped[int] = mapped_column(Integer, index=True)
    media_type: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20))  # 'added', 'downloading', 'available'
    checked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )
```

**Step 3: Update main.py to initialize database**

Add to `backend/src/app/main.py` after imports:

```python
from contextlib import asynccontextmanager
from app.database import init_db
import os


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - runs on startup and shutdown."""
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    init_db()
    yield


# Update FastAPI initialization to use lifespan
app = FastAPI(
    title="Movie Discovery API",
    description="Discover movies and TV shows, integrate with Sonarr/Radarr",
    version="0.1.0",
    lifespan=lifespan,
)
```

**Step 4: Commit**

```bash
git add backend/src/app/database.py backend/src/app/models.py backend/src/app/main.py
git commit -m "feat: add SQLAlchemy models and database setup

- MediaCache for TMDB metadata caching
- Watchlist for user's saved items
- LibraryStatus for Sonarr/Radarr tracking
- Auto-create tables on startup

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 0.3: Create API Schemas (Shared Contracts)

**Files:**
- Create: `backend/src/app/schemas.py`

**Step 1: Create Pydantic schemas**

```python
"""Pydantic schemas for API request/response models."""
from datetime import datetime
from pydantic import BaseModel


# === Media Schemas ===

class MediaBase(BaseModel):
    """Base media information."""

    tmdb_id: int
    media_type: str  # 'movie' or 'show'
    title: str
    overview: str | None = None
    poster_path: str | None = None
    release_date: str | None = None
    vote_average: float | None = None


class MediaResponse(MediaBase):
    """Media item in API responses."""

    library_status: str | None = None  # 'available', 'downloading', 'added', None


class MediaList(BaseModel):
    """List of media items."""

    results: list[MediaResponse]
    page: int = 1
    total_pages: int = 1
    total_results: int = 0


# === Watchlist Schemas ===

class WatchlistAdd(BaseModel):
    """Request to add item to watchlist."""

    tmdb_id: int
    media_type: str
    notes: str | None = None


class WatchlistItem(MediaBase):
    """Watchlist item response."""

    id: int
    added_at: datetime
    notes: str | None = None


class WatchlistResponse(BaseModel):
    """Watchlist list response."""

    items: list[WatchlistItem]
    total: int


# === Sonarr/Radarr Schemas ===

class AddMediaRequest(BaseModel):
    """Request to add media to Sonarr/Radarr."""

    tmdb_id: int
    quality_profile_id: int | None = None


class LibraryStatusResponse(BaseModel):
    """Status of media in Sonarr/Radarr."""

    tmdb_id: int
    media_type: str
    status: str  # 'available', 'downloading', 'added', 'not_found'
    title: str | None = None


class AddMediaResponse(BaseModel):
    """Response after adding media."""

    success: bool
    message: str
    tmdb_id: int
```

**Step 2: Commit**

```bash
git add backend/src/app/schemas.py
git commit -m "feat: add Pydantic API schemas

Defines request/response models for:
- Media discovery endpoints
- Watchlist CRUD operations
- Sonarr/Radarr integration

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 0.4: Create Vue Frontend Structure

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/main.js`
- Create: `frontend/src/App.vue`

**Step 1: Create frontend directory**

```bash
mkdir -p frontend/src/{views,components,services,stores}
```

**Step 2: Create package.json**

```json
{
  "name": "movie-discovery-frontend",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.2.0",
    "pinia": "^2.1.0",
    "axios": "^1.6.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "vite": "^5.0.0"
  }
}
```

**Step 3: Create vite.config.js**

```javascript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

**Step 4: Create index.html**

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Movie Discovery</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.js"></script>
  </body>
</html>
```

**Step 5: Create main.js**

```javascript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'

const app = createApp(App)
app.use(createPinia())
app.mount('#app')
```

**Step 6: Create App.vue**

```vue
<template>
  <div id="app">
    <header>
      <h1>Movie Discovery</h1>
      <nav>
        <a href="#discover">Discover</a>
        <a href="#watchlist">Watchlist</a>
      </nav>
    </header>
    <main>
      <p>App shell ready. Modules coming soon.</p>
    </main>
  </div>
</template>

<script setup>
// App shell - routing and components added in frontend worktree
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: system-ui, -apple-system, sans-serif;
  background: #0f0f0f;
  color: #e0e0e0;
}

#app {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
}

header h1 {
  color: #e50914;
}

nav a {
  color: #e0e0e0;
  text-decoration: none;
  margin-left: 20px;
}

nav a:hover {
  color: #e50914;
}
</style>
```

**Step 7: Commit**

```bash
git add frontend/
git commit -m "feat: initialize Vue 3 frontend structure

- Vite build setup with API proxy
- Pinia for state management
- Basic app shell with dark theme

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 0.5: Create .env.example and README

**Files:**
- Create: `.env.example`
- Create: `README.md`

**Step 1: Create .env.example**

```bash
# TMDB API (get from https://www.themoviedb.org/settings/api)
TMDB_API_KEY=your_tmdb_api_key_here

# Sonarr (get from Sonarr > Settings > General > API Key)
SONARR_URL=http://localhost:8989
SONARR_API_KEY=your_sonarr_api_key_here

# Radarr (get from Radarr > Settings > General > API Key)
RADARR_URL=http://localhost:7878
RADARR_API_KEY=your_radarr_api_key_here

# Database
DATABASE_PATH=./data/movie_discovery.db
```

**Step 2: Create README.md**

```markdown
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
```

**Step 3: Commit**

```bash
git add .env.example README.md
git commit -m "docs: add README and environment template

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Phase 1: Discovery API Module

> Execute in: `.worktrees/discovery-api/`

### Task 1.1: Create TMDB Client

**Files:**
- Create: `backend/src/app/modules/discovery/__init__.py`
- Create: `backend/src/app/modules/discovery/tmdb_client.py`
- Create: `backend/tests/test_tmdb_client.py`

**Step 1: Write the failing test**

```python
"""Tests for TMDB client."""
import pytest
from unittest.mock import AsyncMock, patch

from app.modules.discovery.tmdb_client import TMDBClient


@pytest.fixture
def tmdb_client():
    return TMDBClient(api_key="test_key")


@pytest.mark.asyncio
async def test_get_trending_movies(tmdb_client):
    mock_response = {
        "results": [
            {
                "id": 123,
                "title": "Test Movie",
                "overview": "A test movie",
                "poster_path": "/test.jpg",
                "release_date": "2024-01-01",
                "vote_average": 8.5,
            }
        ],
        "page": 1,
        "total_pages": 10,
        "total_results": 100,
    }

    with patch.object(tmdb_client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await tmdb_client.get_trending_movies()

    assert len(result["results"]) == 1
    assert result["results"][0]["title"] == "Test Movie"


@pytest.mark.asyncio
async def test_search_movies(tmdb_client):
    mock_response = {
        "results": [{"id": 456, "title": "Search Result"}],
        "page": 1,
        "total_pages": 1,
        "total_results": 1,
    }

    with patch.object(tmdb_client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await tmdb_client.search("test query")

    mock_get.assert_called_once()
    assert result["results"][0]["title"] == "Search Result"
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_tmdb_client.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Create the TMDB client**

Create `backend/src/app/modules/__init__.py`:
```python
"""Backend modules."""
```

Create `backend/src/app/modules/discovery/__init__.py`:
```python
"""Discovery module - TMDB integration."""
from .tmdb_client import TMDBClient
from .router import router

__all__ = ["TMDBClient", "router"]
```

Create `backend/src/app/modules/discovery/tmdb_client.py`:
```python
"""TMDB API client."""
import httpx
from typing import Any


class TMDBClient:
    """Client for The Movie Database API."""

    BASE_URL = "https://api.themoviedb.org/3"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def _get(self, endpoint: str, params: dict | None = None) -> dict[str, Any]:
        """Make GET request to TMDB API."""
        params = params or {}
        params["api_key"] = self.api_key

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.BASE_URL}{endpoint}", params=params)
            response.raise_for_status()
            return response.json()

    async def get_trending_movies(self, page: int = 1) -> dict[str, Any]:
        """Get trending movies."""
        return await self._get("/trending/movie/week", {"page": page})

    async def get_trending_shows(self, page: int = 1) -> dict[str, Any]:
        """Get trending TV shows."""
        return await self._get("/trending/tv/week", {"page": page})

    async def search(self, query: str, page: int = 1) -> dict[str, Any]:
        """Search for movies and TV shows."""
        return await self._get("/search/multi", {"query": query, "page": page})

    async def get_similar(self, tmdb_id: int, media_type: str) -> dict[str, Any]:
        """Get similar movies or shows."""
        endpoint = f"/{media_type}/{tmdb_id}/similar"
        return await self._get(endpoint)

    async def get_details(self, tmdb_id: int, media_type: str) -> dict[str, Any]:
        """Get movie or show details."""
        endpoint = f"/{media_type}/{tmdb_id}"
        return await self._get(endpoint)
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_tmdb_client.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/app/modules/ backend/tests/test_tmdb_client.py
git commit -m "feat(discovery): add TMDB API client

- Trending movies and TV shows
- Multi-search endpoint
- Similar titles lookup
- Full test coverage with mocked responses

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 1.2: Create Discovery Router

**Files:**
- Create: `backend/src/app/modules/discovery/router.py`
- Create: `backend/tests/test_discovery_router.py`

**Step 1: Write the failing test**

```python
"""Tests for discovery API endpoints."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_get_trending_movies(client):
    mock_response = {
        "results": [
            {
                "id": 123,
                "title": "Test Movie",
                "overview": "A test",
                "poster_path": "/test.jpg",
                "release_date": "2024-01-01",
                "vote_average": 8.5,
            }
        ],
        "page": 1,
        "total_pages": 1,
        "total_results": 1,
    }

    with patch(
        "app.modules.discovery.router.tmdb_client.get_trending_movies",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = mock_response
        response = client.get("/api/discover/movies/trending")

    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 1


def test_search(client):
    mock_response = {
        "results": [{"id": 456, "title": "Search Result", "media_type": "movie"}],
        "page": 1,
        "total_pages": 1,
        "total_results": 1,
    }

    with patch(
        "app.modules.discovery.router.tmdb_client.search",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = mock_response
        response = client.get("/api/discover/search?q=test")

    assert response.status_code == 200
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_discovery_router.py -v`
Expected: FAIL

**Step 3: Create the router**

```python
"""Discovery API routes."""
from fastapi import APIRouter, Query

from app.config import settings
from app.schemas import MediaList, MediaResponse
from .tmdb_client import TMDBClient

router = APIRouter(prefix="/api/discover", tags=["discovery"])

tmdb_client = TMDBClient(api_key=settings.tmdb_api_key)


def _transform_tmdb_result(item: dict, media_type: str | None = None) -> MediaResponse:
    """Transform TMDB result to our schema."""
    mtype = media_type or item.get("media_type", "movie")
    title = item.get("title") or item.get("name", "Unknown")
    release = item.get("release_date") or item.get("first_air_date")

    return MediaResponse(
        tmdb_id=item["id"],
        media_type=mtype,
        title=title,
        overview=item.get("overview"),
        poster_path=item.get("poster_path"),
        release_date=release,
        vote_average=item.get("vote_average"),
        library_status=None,
    )


@router.get("/movies/trending", response_model=MediaList)
async def get_trending_movies(page: int = Query(1, ge=1)):
    """Get trending movies from TMDB."""
    data = await tmdb_client.get_trending_movies(page=page)
    return MediaList(
        results=[_transform_tmdb_result(item, "movie") for item in data["results"]],
        page=data["page"],
        total_pages=data["total_pages"],
        total_results=data["total_results"],
    )


@router.get("/shows/trending", response_model=MediaList)
async def get_trending_shows(page: int = Query(1, ge=1)):
    """Get trending TV shows from TMDB."""
    data = await tmdb_client.get_trending_shows(page=page)
    return MediaList(
        results=[_transform_tmdb_result(item, "show") for item in data["results"]],
        page=data["page"],
        total_pages=data["total_pages"],
        total_results=data["total_results"],
    )


@router.get("/search", response_model=MediaList)
async def search(q: str = Query(..., min_length=1), page: int = Query(1, ge=1)):
    """Search for movies and TV shows."""
    data = await tmdb_client.search(query=q, page=page)
    # Filter to only movies and TV shows
    results = [
        _transform_tmdb_result(item)
        for item in data["results"]
        if item.get("media_type") in ("movie", "tv")
    ]
    return MediaList(
        results=results,
        page=data["page"],
        total_pages=data["total_pages"],
        total_results=len(results),
    )


@router.get("/similar/{tmdb_id}", response_model=MediaList)
async def get_similar(tmdb_id: int, media_type: str = Query(...)):
    """Get similar movies or shows."""
    mt = "tv" if media_type == "show" else media_type
    data = await tmdb_client.get_similar(tmdb_id=tmdb_id, media_type=mt)
    return MediaList(
        results=[_transform_tmdb_result(item, media_type) for item in data["results"]],
        page=1,
        total_pages=1,
        total_results=len(data["results"]),
    )
```

**Step 4: Register router in main.py**

Add to `backend/src/app/main.py`:
```python
from app.modules.discovery import router as discovery_router

# After app initialization
app.include_router(discovery_router)
```

**Step 5: Run test to verify it passes**

Run: `cd backend && pytest tests/test_discovery_router.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add backend/
git commit -m "feat(discovery): add API endpoints

- GET /api/discover/movies/trending
- GET /api/discover/shows/trending
- GET /api/discover/search
- GET /api/discover/similar/{tmdb_id}

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Phase 2: Watchlist Module

> Execute in: `.worktrees/watchlist/`

### Task 2.1: Create Watchlist Service

**Files:**
- Create: `backend/src/app/modules/watchlist/__init__.py`
- Create: `backend/src/app/modules/watchlist/service.py`
- Create: `backend/tests/test_watchlist_service.py`

**Step 1: Write the failing test**

```python
"""Tests for watchlist service."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.modules.watchlist.service import WatchlistService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def service(db_session):
    return WatchlistService(db_session)


def test_add_to_watchlist(service):
    item = service.add(tmdb_id=123, media_type="movie", notes="Test note")
    assert item.tmdb_id == 123
    assert item.media_type == "movie"
    assert item.notes == "Test note"


def test_get_watchlist(service):
    service.add(tmdb_id=123, media_type="movie")
    service.add(tmdb_id=456, media_type="show")

    items = service.get_all()
    assert len(items) == 2


def test_remove_from_watchlist(service):
    item = service.add(tmdb_id=123, media_type="movie")
    service.remove(item.id)

    items = service.get_all()
    assert len(items) == 0


def test_duplicate_add_returns_existing(service):
    item1 = service.add(tmdb_id=123, media_type="movie")
    item2 = service.add(tmdb_id=123, media_type="movie")
    assert item1.id == item2.id
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_watchlist_service.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Create watchlist service**

Create `backend/src/app/modules/watchlist/__init__.py`:
```python
"""Watchlist module."""
from .service import WatchlistService
from .router import router

__all__ = ["WatchlistService", "router"]
```

Create `backend/src/app/modules/watchlist/service.py`:
```python
"""Watchlist business logic."""
from sqlalchemy.orm import Session

from app.models import Watchlist


class WatchlistService:
    """Service for managing watchlist items."""

    def __init__(self, db: Session):
        self.db = db

    def add(self, tmdb_id: int, media_type: str, notes: str | None = None) -> Watchlist:
        """Add item to watchlist. Returns existing if duplicate."""
        existing = (
            self.db.query(Watchlist)
            .filter(Watchlist.tmdb_id == tmdb_id, Watchlist.media_type == media_type)
            .first()
        )
        if existing:
            return existing

        item = Watchlist(tmdb_id=tmdb_id, media_type=media_type, notes=notes)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def get_all(self) -> list[Watchlist]:
        """Get all watchlist items."""
        return self.db.query(Watchlist).order_by(Watchlist.added_at.desc()).all()

    def get_by_id(self, item_id: int) -> Watchlist | None:
        """Get watchlist item by ID."""
        return self.db.query(Watchlist).filter(Watchlist.id == item_id).first()

    def remove(self, item_id: int) -> bool:
        """Remove item from watchlist."""
        item = self.get_by_id(item_id)
        if not item:
            return False
        self.db.delete(item)
        self.db.commit()
        return True
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_watchlist_service.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/app/modules/watchlist/ backend/tests/test_watchlist_service.py
git commit -m "feat(watchlist): add watchlist service

- Add/remove items from watchlist
- Duplicate detection returns existing
- Ordered by most recently added

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 2.2: Create Watchlist Router

**Files:**
- Create: `backend/src/app/modules/watchlist/router.py`
- Create: `backend/tests/test_watchlist_router.py`

**Step 1: Write the failing test**

```python
"""Tests for watchlist API endpoints."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db


# Create test database
engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine)
TestSession = sessionmaker(bind=engine)


def override_get_db():
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return TestClient(app)


def test_add_to_watchlist(client):
    response = client.post(
        "/api/watchlist",
        json={"tmdb_id": 123, "media_type": "movie", "notes": "Want to watch"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tmdb_id"] == 123


def test_get_watchlist(client):
    client.post("/api/watchlist", json={"tmdb_id": 123, "media_type": "movie"})
    client.post("/api/watchlist", json={"tmdb_id": 456, "media_type": "show"})

    response = client.get("/api/watchlist")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2


def test_delete_from_watchlist(client):
    add_response = client.post(
        "/api/watchlist", json={"tmdb_id": 123, "media_type": "movie"}
    )
    item_id = add_response.json()["id"]

    delete_response = client.delete(f"/api/watchlist/{item_id}")
    assert delete_response.status_code == 200

    get_response = client.get("/api/watchlist")
    assert get_response.json()["total"] == 0
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_watchlist_router.py -v`
Expected: FAIL

**Step 3: Create the router**

```python
"""Watchlist API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import WatchlistAdd, WatchlistItem, WatchlistResponse
from .service import WatchlistService

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


def get_service(db: Session = Depends(get_db)) -> WatchlistService:
    return WatchlistService(db)


@router.get("", response_model=WatchlistResponse)
async def get_watchlist(service: WatchlistService = Depends(get_service)):
    """Get all watchlist items."""
    items = service.get_all()
    return WatchlistResponse(
        items=[
            WatchlistItem(
                id=item.id,
                tmdb_id=item.tmdb_id,
                media_type=item.media_type,
                title=f"TMDB:{item.tmdb_id}",  # Would be enriched with cache
                added_at=item.added_at,
                notes=item.notes,
            )
            for item in items
        ],
        total=len(items),
    )


@router.post("", response_model=WatchlistItem)
async def add_to_watchlist(
    data: WatchlistAdd, service: WatchlistService = Depends(get_service)
):
    """Add item to watchlist."""
    item = service.add(
        tmdb_id=data.tmdb_id, media_type=data.media_type, notes=data.notes
    )
    return WatchlistItem(
        id=item.id,
        tmdb_id=item.tmdb_id,
        media_type=item.media_type,
        title=f"TMDB:{item.tmdb_id}",
        added_at=item.added_at,
        notes=item.notes,
    )


@router.delete("/{item_id}")
async def remove_from_watchlist(
    item_id: int, service: WatchlistService = Depends(get_service)
):
    """Remove item from watchlist."""
    if not service.remove(item_id):
        raise HTTPException(status_code=404, detail="Item not found")
    return {"success": True}
```

**Step 4: Register router in main.py**

Add to `backend/src/app/main.py`:
```python
from app.modules.watchlist import router as watchlist_router

app.include_router(watchlist_router)
```

**Step 5: Run test to verify it passes**

Run: `cd backend && pytest tests/test_watchlist_router.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add backend/
git commit -m "feat(watchlist): add API endpoints

- GET /api/watchlist - list all items
- POST /api/watchlist - add item
- DELETE /api/watchlist/{id} - remove item

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Phase 3: Sonarr/Radarr Module

> Execute in: `.worktrees/sonarr-radarr/`

### Task 3.1: Create Radarr Client

**Files:**
- Create: `backend/src/app/modules/radarr/__init__.py`
- Create: `backend/src/app/modules/radarr/client.py`
- Create: `backend/tests/test_radarr_client.py`

**Step 1: Write the failing test**

```python
"""Tests for Radarr client."""
import pytest
from unittest.mock import AsyncMock, patch

from app.modules.radarr.client import RadarrClient


@pytest.fixture
def client():
    return RadarrClient(url="http://localhost:7878", api_key="test_key")


@pytest.mark.asyncio
async def test_get_movie_by_tmdb_id(client):
    mock_response = [
        {"id": 1, "tmdbId": 123, "title": "Test Movie", "hasFile": True}
    ]

    with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await client.get_movie_by_tmdb_id(123)

    assert result is not None
    assert result["tmdbId"] == 123


@pytest.mark.asyncio
async def test_get_movie_not_found(client):
    with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = []
        result = await client.get_movie_by_tmdb_id(999)

    assert result is None


@pytest.mark.asyncio
async def test_add_movie(client):
    mock_lookup = [{"tmdbId": 123, "title": "Test Movie", "year": 2024}]
    mock_add = {"id": 1, "tmdbId": 123, "title": "Test Movie"}

    with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
        with patch.object(client, "_post", new_callable=AsyncMock) as mock_post:
            mock_get.return_value = mock_lookup
            mock_post.return_value = mock_add
            result = await client.add_movie(tmdb_id=123)

    assert result["tmdbId"] == 123
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_radarr_client.py -v`
Expected: FAIL

**Step 3: Create Radarr client**

Create `backend/src/app/modules/radarr/__init__.py`:
```python
"""Radarr module."""
from .client import RadarrClient
from .router import router

__all__ = ["RadarrClient", "router"]
```

Create `backend/src/app/modules/radarr/client.py`:
```python
"""Radarr API client."""
import httpx
from typing import Any


class RadarrClient:
    """Client for Radarr API."""

    def __init__(self, url: str, api_key: str):
        self.url = url.rstrip("/")
        self.api_key = api_key

    async def _get(self, endpoint: str, params: dict | None = None) -> Any:
        """Make GET request to Radarr API."""
        headers = {"X-Api-Key": self.api_key}
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.url}/api/v3{endpoint}",
                headers=headers,
                params=params,
            )
            response.raise_for_status()
            return response.json()

    async def _post(self, endpoint: str, data: dict) -> Any:
        """Make POST request to Radarr API."""
        headers = {"X-Api-Key": self.api_key}
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.url}/api/v3{endpoint}",
                headers=headers,
                json=data,
            )
            response.raise_for_status()
            return response.json()

    async def get_movie_by_tmdb_id(self, tmdb_id: int) -> dict | None:
        """Get movie from library by TMDB ID."""
        movies = await self._get("/movie", {"tmdbId": tmdb_id})
        return movies[0] if movies else None

    async def lookup_movie(self, tmdb_id: int) -> dict | None:
        """Lookup movie info from TMDB via Radarr."""
        results = await self._get("/movie/lookup", {"term": f"tmdb:{tmdb_id}"})
        return results[0] if results else None

    async def add_movie(
        self,
        tmdb_id: int,
        quality_profile_id: int = 1,
        root_folder_path: str | None = None,
    ) -> dict:
        """Add movie to Radarr."""
        movie = await self.lookup_movie(tmdb_id)
        if not movie:
            raise ValueError(f"Movie not found: {tmdb_id}")

        # Get root folder if not specified
        if not root_folder_path:
            folders = await self._get("/rootfolder")
            root_folder_path = folders[0]["path"] if folders else "/movies"

        movie["qualityProfileId"] = quality_profile_id
        movie["rootFolderPath"] = root_folder_path
        movie["monitored"] = True
        movie["addOptions"] = {"searchForMovie": True}

        return await self._post("/movie", movie)

    async def get_status(self, tmdb_id: int) -> str:
        """Get movie status: 'available', 'downloading', 'added', 'not_found'."""
        movie = await self.get_movie_by_tmdb_id(tmdb_id)
        if not movie:
            return "not_found"
        if movie.get("hasFile"):
            return "available"
        if movie.get("isAvailable") is False:
            return "downloading"
        return "added"
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_radarr_client.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/app/modules/radarr/ backend/tests/test_radarr_client.py
git commit -m "feat(radarr): add Radarr API client

- Lookup movies by TMDB ID
- Add movies to library with auto-search
- Get movie status (available/downloading/added)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 3.2: Create Sonarr Client

**Files:**
- Create: `backend/src/app/modules/sonarr/__init__.py`
- Create: `backend/src/app/modules/sonarr/client.py`
- Create: `backend/tests/test_sonarr_client.py`

*(Similar structure to Radarr - uses /api/v3/series endpoints)*

**Step 1: Write test, Step 2: Verify fails, Step 3: Implement**

Create `backend/src/app/modules/sonarr/client.py`:
```python
"""Sonarr API client."""
import httpx
from typing import Any


class SonarrClient:
    """Client for Sonarr API."""

    def __init__(self, url: str, api_key: str):
        self.url = url.rstrip("/")
        self.api_key = api_key

    async def _get(self, endpoint: str, params: dict | None = None) -> Any:
        """Make GET request to Sonarr API."""
        headers = {"X-Api-Key": self.api_key}
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.url}/api/v3{endpoint}",
                headers=headers,
                params=params,
            )
            response.raise_for_status()
            return response.json()

    async def _post(self, endpoint: str, data: dict) -> Any:
        """Make POST request to Sonarr API."""
        headers = {"X-Api-Key": self.api_key}
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.url}/api/v3{endpoint}",
                headers=headers,
                json=data,
            )
            response.raise_for_status()
            return response.json()

    async def get_series_by_tvdb_id(self, tvdb_id: int) -> dict | None:
        """Get series from library by TVDB ID."""
        series_list = await self._get("/series")
        for series in series_list:
            if series.get("tvdbId") == tvdb_id:
                return series
        return None

    async def lookup_series(self, tmdb_id: int) -> dict | None:
        """Lookup series info via Sonarr (uses TVDB internally)."""
        results = await self._get("/series/lookup", {"term": f"tmdb:{tmdb_id}"})
        return results[0] if results else None

    async def add_series(
        self,
        tmdb_id: int,
        quality_profile_id: int = 1,
        root_folder_path: str | None = None,
    ) -> dict:
        """Add series to Sonarr."""
        series = await self.lookup_series(tmdb_id)
        if not series:
            raise ValueError(f"Series not found: {tmdb_id}")

        if not root_folder_path:
            folders = await self._get("/rootfolder")
            root_folder_path = folders[0]["path"] if folders else "/tv"

        series["qualityProfileId"] = quality_profile_id
        series["rootFolderPath"] = root_folder_path
        series["monitored"] = True
        series["addOptions"] = {"searchForMissingEpisodes": True}

        return await self._post("/series", series)

    async def get_status(self, tmdb_id: int) -> str:
        """Get series status."""
        series = await self.lookup_series(tmdb_id)
        if not series:
            return "not_found"

        existing = await self.get_series_by_tvdb_id(series.get("tvdbId", 0))
        if not existing:
            return "not_found"

        stats = existing.get("statistics", {})
        if stats.get("percentOfEpisodes", 0) == 100:
            return "available"
        if stats.get("episodeFileCount", 0) > 0:
            return "downloading"
        return "added"
```

**Step 4: Run tests, Step 5: Commit**

```bash
git add backend/src/app/modules/sonarr/ backend/tests/test_sonarr_client.py
git commit -m "feat(sonarr): add Sonarr API client

- Lookup series by TMDB ID
- Add series with auto-search for episodes
- Get series status

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 3.3: Create Radarr/Sonarr Routers

**Files:**
- Create: `backend/src/app/modules/radarr/router.py`
- Create: `backend/src/app/modules/sonarr/router.py`

*(Routers expose status check and add endpoints)*

Create `backend/src/app/modules/radarr/router.py`:
```python
"""Radarr API routes."""
from fastapi import APIRouter, HTTPException

from app.config import settings
from app.schemas import AddMediaRequest, AddMediaResponse, LibraryStatusResponse
from .client import RadarrClient

router = APIRouter(prefix="/api/radarr", tags=["radarr"])

client = RadarrClient(url=settings.radarr_url, api_key=settings.radarr_api_key)


@router.get("/status/{tmdb_id}", response_model=LibraryStatusResponse)
async def get_movie_status(tmdb_id: int):
    """Check if movie is in Radarr library."""
    status = await client.get_status(tmdb_id)
    movie = await client.lookup_movie(tmdb_id)
    return LibraryStatusResponse(
        tmdb_id=tmdb_id,
        media_type="movie",
        status=status,
        title=movie.get("title") if movie else None,
    )


@router.post("/add", response_model=AddMediaResponse)
async def add_movie(data: AddMediaRequest):
    """Add movie to Radarr."""
    try:
        result = await client.add_movie(
            tmdb_id=data.tmdb_id,
            quality_profile_id=data.quality_profile_id or 1,
        )
        return AddMediaResponse(
            success=True,
            message=f"Added {result.get('title', 'movie')} to Radarr",
            tmdb_id=data.tmdb_id,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

Create similar `sonarr/router.py` and register both in main.py.

**Commit:**
```bash
git add backend/
git commit -m "feat(radarr,sonarr): add API endpoints

- GET /api/radarr/status/{tmdb_id}
- POST /api/radarr/add
- GET /api/sonarr/status/{tmdb_id}
- POST /api/sonarr/add

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Phase 4: Frontend Module

> Execute in: `.worktrees/frontend/`

### Task 4.1: Create API Service Layer

**Files:**
- Create: `frontend/src/services/api.js`
- Create: `frontend/src/services/discover.js`
- Create: `frontend/src/services/library.js`
- Create: `frontend/src/services/watchlist.js`

**Step 1: Create base API client**

```javascript
// frontend/src/services/api.js
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error:', error.response?.data || error.message)
    throw error
  }
)

export default api
```

**Step 2: Create service modules**

```javascript
// frontend/src/services/discover.js
import api from './api'

export const discoverService = {
  getTrendingMovies: (page = 1) => api.get(`/discover/movies/trending?page=${page}`),
  getTrendingShows: (page = 1) => api.get(`/discover/shows/trending?page=${page}`),
  search: (query, page = 1) => api.get(`/discover/search?q=${query}&page=${page}`),
  getSimilar: (tmdbId, mediaType) => api.get(`/discover/similar/${tmdbId}?media_type=${mediaType}`),
}
```

```javascript
// frontend/src/services/library.js
import api from './api'

export const libraryService = {
  getMovieStatus: (tmdbId) => api.get(`/radarr/status/${tmdbId}`),
  addMovie: (tmdbId) => api.post('/radarr/add', { tmdb_id: tmdbId }),
  getShowStatus: (tmdbId) => api.get(`/sonarr/status/${tmdbId}`),
  addShow: (tmdbId) => api.post('/sonarr/add', { tmdb_id: tmdbId }),
}
```

```javascript
// frontend/src/services/watchlist.js
import api from './api'

export const watchlistService = {
  getAll: () => api.get('/watchlist'),
  add: (tmdbId, mediaType, notes = null) =>
    api.post('/watchlist', { tmdb_id: tmdbId, media_type: mediaType, notes }),
  remove: (id) => api.delete(`/watchlist/${id}`),
}
```

**Step 3: Commit**

```bash
git add frontend/src/services/
git commit -m "feat(frontend): add API service layer

- Axios client with error handling
- Discovery, library, and watchlist services

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 4.2: Create MediaCard Component

**Files:**
- Create: `frontend/src/components/MediaCard.vue`
- Create: `frontend/src/components/StatusBadge.vue`

```vue
<!-- frontend/src/components/StatusBadge.vue -->
<template>
  <span :class="['badge', status]">
    {{ label }}
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: { type: String, default: null }
})

const label = computed(() => {
  switch (props.status) {
    case 'available': return 'In Library'
    case 'downloading': return 'Downloading'
    case 'added': return 'Added'
    default: return 'Add'
  }
})
</script>

<style scoped>
.badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}
.available { background: #22c55e; color: white; }
.downloading { background: #eab308; color: black; }
.added { background: #3b82f6; color: white; }
.badge:not(.available):not(.downloading):not(.added) {
  background: #e50914;
  color: white;
  cursor: pointer;
}
</style>
```

```vue
<!-- frontend/src/components/MediaCard.vue -->
<template>
  <div class="media-card">
    <div class="poster">
      <img
        v-if="media.poster_path"
        :src="`https://image.tmdb.org/t/p/w300${media.poster_path}`"
        :alt="media.title"
      />
      <div v-else class="no-poster">No Image</div>
      <StatusBadge
        :status="media.library_status"
        class="status-overlay"
        @click="handleAdd"
      />
    </div>
    <div class="info">
      <h3>{{ media.title }}</h3>
      <p class="meta">
        {{ media.release_date?.slice(0, 4) }}
        <span v-if="media.vote_average">• {{ media.vote_average.toFixed(1) }}</span>
      </p>
    </div>
  </div>
</template>

<script setup>
import StatusBadge from './StatusBadge.vue'

const props = defineProps({
  media: { type: Object, required: true }
})

const emit = defineEmits(['add'])

const handleAdd = () => {
  if (!props.media.library_status) {
    emit('add', props.media)
  }
}
</script>

<style scoped>
.media-card {
  background: #1a1a1a;
  border-radius: 8px;
  overflow: hidden;
  transition: transform 0.2s;
}
.media-card:hover {
  transform: scale(1.02);
}
.poster {
  position: relative;
  aspect-ratio: 2/3;
}
.poster img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.no-poster {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #333;
  color: #666;
}
.status-overlay {
  position: absolute;
  bottom: 8px;
  right: 8px;
}
.info {
  padding: 12px;
}
.info h3 {
  font-size: 14px;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.meta {
  font-size: 12px;
  color: #888;
}
</style>
```

**Commit:**
```bash
git add frontend/src/components/
git commit -m "feat(frontend): add MediaCard and StatusBadge components

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 4.3: Create Views and Router

**Files:**
- Create: `frontend/src/views/DiscoverView.vue`
- Create: `frontend/src/views/WatchlistView.vue`
- Create: `frontend/src/router/index.js`

*(DiscoverView shows trending grid, WatchlistView shows saved items)*

---

### Task 4.4: Create Pinia Store

**Files:**
- Create: `frontend/src/stores/appStore.js`

```javascript
import { defineStore } from 'pinia'
import { discoverService } from '@/services/discover'
import { libraryService } from '@/services/library'
import { watchlistService } from '@/services/watchlist'

export const useAppStore = defineStore('app', {
  state: () => ({
    trendingMovies: [],
    trendingShows: [],
    searchResults: [],
    watchlist: [],
    loading: false,
    error: null,
  }),

  actions: {
    async fetchTrendingMovies() {
      this.loading = true
      try {
        const data = await discoverService.getTrendingMovies()
        this.trendingMovies = data.results
      } catch (e) {
        this.error = e.message
      } finally {
        this.loading = false
      }
    },

    async addToLibrary(media) {
      try {
        if (media.media_type === 'movie') {
          await libraryService.addMovie(media.tmdb_id)
        } else {
          await libraryService.addShow(media.tmdb_id)
        }
        media.library_status = 'added'
      } catch (e) {
        this.error = e.message
      }
    },

    async fetchWatchlist() {
      const data = await watchlistService.getAll()
      this.watchlist = data.items
    },
  },
})
```

---

## Phase 5: Integration (main branch)

> Execute in: `movie_discovery/` (main workspace)

### Task 5.1: Merge Feature Branches

```bash
git merge feature/discovery-api --no-ff -m "Merge discovery-api module"
git merge feature/watchlist --no-ff -m "Merge watchlist module"
git merge feature/sonarr-radarr --no-ff -m "Merge sonarr-radarr module"
git merge feature/frontend --no-ff -m "Merge frontend module"
```

### Task 5.2: Integration Testing

Run full test suite and verify all endpoints work together.

### Task 5.3: Clean Up Worktrees

```bash
git worktree remove .worktrees/discovery-api
git worktree remove .worktrees/sonarr-radarr
git worktree remove .worktrees/watchlist
git worktree remove .worktrees/frontend
```

---

## Parallel Execution Summary

| Worktree | Tasks | Can Start After |
|----------|-------|-----------------|
| main | Phase 0 (setup) | Immediately |
| discovery-api | Phase 1 | Phase 0 complete |
| watchlist | Phase 2 | Phase 0 complete |
| sonarr-radarr | Phase 3 | Phase 0 complete |
| frontend | Phase 4 | Phase 0 complete |
| main | Phase 5 (integration) | All phases complete |

**Phases 1-4 can run in parallel** after Phase 0 completes.
