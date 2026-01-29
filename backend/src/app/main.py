"""FastAPI application entry point."""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.modules.discovery import router as discovery_router, genres_router
from app.modules.watchlist import router as watchlist_router
from app.modules.radarr import router as radarr_router
from app.modules.sonarr import router as sonarr_router
from app.modules.settings.router import router as settings_router
from app.modules.library import router as library_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - runs on startup and shutdown."""
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    init_db()
    yield


app = FastAPI(
    title="Movie Discovery API",
    description="Discover movies and TV shows, integrate with Sonarr/Radarr",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(discovery_router)
app.include_router(genres_router)
app.include_router(watchlist_router)
app.include_router(radarr_router)
app.include_router(sonarr_router)
app.include_router(settings_router)
app.include_router(library_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
