"""FastAPI application entry point."""
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database import init_db
from app.modules.discovery import router as discovery_router, genres_router
from app.modules.watchlist import router as watchlist_router
from app.modules.radarr import router as radarr_router
from app.modules.sonarr import router as sonarr_router
from app.modules.settings.router import router as settings_router
from app.modules.library import router as library_router
from app.modules.calendar import router as calendar_router
from app.modules.recommendations import router as recommendations_router
from app.modules.clients import close_all_clients


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - runs on startup and shutdown."""
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    init_db()
    yield
    await close_all_clients()


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


@app.exception_handler(httpx.TimeoutException)
async def upstream_timeout_handler(
    request: Request, exc: httpx.TimeoutException
) -> JSONResponse:
    """Safety net: a slow external service (Radarr/Sonarr) -> 504, not raw 500."""
    return JSONResponse(
        status_code=504, content={"detail": "Upstream service timed out"}
    )


@app.exception_handler(httpx.RequestError)
async def upstream_unreachable_handler(
    request: Request, exc: httpx.RequestError
) -> JSONResponse:
    """Safety net: an unreachable external service (e.g. ConnectError) -> 503."""
    return JSONResponse(
        status_code=503, content={"detail": "Upstream service unreachable"}
    )


@app.exception_handler(httpx.HTTPStatusError)
async def upstream_error_handler(
    request: Request, exc: httpx.HTTPStatusError
) -> JSONResponse:
    """Safety net: an error status from an external service -> 502."""
    return JSONResponse(
        status_code=502, content={"detail": "Upstream service error"}
    )


# Include routers
app.include_router(discovery_router)
app.include_router(genres_router)
app.include_router(watchlist_router)
app.include_router(radarr_router)
app.include_router(sonarr_router)
app.include_router(settings_router)
app.include_router(library_router)
app.include_router(calendar_router)
app.include_router(recommendations_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
