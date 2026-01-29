"""Tests for Settings Pydantic schemas."""
import pytest
from pydantic import ValidationError
from app.modules.settings.schemas import (
    SettingsUpdate,
    SettingsResponse,
    ConnectionTestRequest,
    ConnectionTestResponse,
)


def test_settings_update_valid():
    """SettingsUpdate should accept valid data."""
    data = SettingsUpdate(
        tmdb_api_key="abc123",
        radarr_url="http://localhost:7878",
        radarr_api_key="radarr-key",
        sonarr_url="http://localhost:8989",
        sonarr_api_key="sonarr-key",
    )
    assert data.tmdb_api_key == "abc123"


def test_settings_update_optional_fields():
    """SettingsUpdate should allow partial updates."""
    data = SettingsUpdate(tmdb_api_key="abc123")
    assert data.tmdb_api_key == "abc123"
    assert data.radarr_url is None


def test_settings_response_masks_keys():
    """SettingsResponse should have masked key fields."""
    data = SettingsResponse(
        tmdb_api_key_masked="********1234",
        radarr_url="http://localhost:7878",
        radarr_api_key_masked="********5678",
        sonarr_url="http://localhost:8989",
        sonarr_api_key_masked="********9012",
        has_tmdb=True,
        has_radarr=True,
        has_sonarr=True,
    )
    # Check that masked fields exist
    assert data.tmdb_api_key_masked == "********1234"
    assert data.has_tmdb is True


def test_connection_test_request():
    """ConnectionTestRequest should validate service type."""
    data = ConnectionTestRequest(service="tmdb")
    assert data.service == "tmdb"


def test_connection_test_request_invalid_service():
    """ConnectionTestRequest should reject invalid service types."""
    with pytest.raises(ValidationError):
        ConnectionTestRequest(service="invalid")


def test_connection_test_response():
    """ConnectionTestResponse should have success and message."""
    data = ConnectionTestResponse(success=True, message="Connected!")
    assert data.success is True
    assert data.message == "Connected!"
