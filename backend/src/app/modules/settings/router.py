"""API router for settings endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import httpx

from app.database import get_db
from app.config import get_setting
from app.modules.settings.service import SettingsService
from app.modules.settings.schemas import (
    SettingsUpdate,
    SettingsResponse,
    ConnectionTestRequest,
    ConnectionTestResponse,
)

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=SettingsResponse)
def get_settings(db: Session = Depends(get_db)):
    """Get current settings with masked sensitive values."""
    service = SettingsService(db)
    return service.get_settings()


@router.put("", response_model=SettingsResponse)
def update_settings(update: SettingsUpdate, db: Session = Depends(get_db)):
    """Update settings."""
    service = SettingsService(db)
    service.update_settings(update)
    return service.get_settings()


@router.post("/test", response_model=ConnectionTestResponse)
async def test_connection(request: ConnectionTestRequest, db: Session = Depends(get_db)):
    """Test connection to a service."""
    service = SettingsService(db)

    if request.service == "tmdb":
        api_key = get_setting("tmdb_api_key")
        if not api_key:
            return ConnectionTestResponse(success=False, message="TMDB API key not configured")
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"https://api.themoviedb.org/3/configuration?api_key={api_key}"
                )
                if resp.status_code == 200:
                    return ConnectionTestResponse(success=True, message="TMDB connection successful")
                return ConnectionTestResponse(success=False, message=f"TMDB error: {resp.status_code}")
        except Exception as e:
            return ConnectionTestResponse(success=False, message=f"Connection failed: {str(e)}")

    elif request.service == "radarr":
        url = get_setting("radarr_url")
        api_key = get_setting("radarr_api_key")
        if not url or not api_key:
            return ConnectionTestResponse(success=False, message="Radarr not configured")
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{url.rstrip('/')}/api/v3/system/status",
                    headers={"X-Api-Key": api_key}
                )
                if resp.status_code == 200:
                    return ConnectionTestResponse(success=True, message="Radarr connection successful")
                return ConnectionTestResponse(success=False, message=f"Radarr error: {resp.status_code}")
        except Exception as e:
            return ConnectionTestResponse(success=False, message=f"Connection failed: {str(e)}")

    elif request.service == "sonarr":
        url = get_setting("sonarr_url")
        api_key = get_setting("sonarr_api_key")
        if not url or not api_key:
            return ConnectionTestResponse(success=False, message="Sonarr not configured")
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{url.rstrip('/')}/api/v3/system/status",
                    headers={"X-Api-Key": api_key}
                )
                if resp.status_code == 200:
                    return ConnectionTestResponse(success=True, message="Sonarr connection successful")
                return ConnectionTestResponse(success=False, message=f"Sonarr error: {resp.status_code}")
        except Exception as e:
            return ConnectionTestResponse(success=False, message=f"Connection failed: {str(e)}")

    return ConnectionTestResponse(success=False, message="Unknown service")
