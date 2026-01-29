"""Pydantic schemas for settings API."""
from typing import Optional, Literal
from pydantic import BaseModel


class SettingsUpdate(BaseModel):
    """Request schema for updating settings."""

    tmdb_api_key: Optional[str] = None
    radarr_url: Optional[str] = None
    radarr_api_key: Optional[str] = None
    sonarr_url: Optional[str] = None
    sonarr_api_key: Optional[str] = None


class SettingsResponse(BaseModel):
    """Response schema with masked API keys."""

    tmdb_api_key_masked: Optional[str] = None
    radarr_url: Optional[str] = None
    radarr_api_key_masked: Optional[str] = None
    sonarr_url: Optional[str] = None
    sonarr_api_key_masked: Optional[str] = None
    has_tmdb: bool = False
    has_radarr: bool = False
    has_sonarr: bool = False


class ConnectionTestRequest(BaseModel):
    """Request to test a service connection."""

    service: Literal["tmdb", "radarr", "sonarr"]


class ConnectionTestResponse(BaseModel):
    """Response from connection test."""

    success: bool
    message: str
