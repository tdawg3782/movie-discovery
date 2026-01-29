"""Tests for Settings service."""
import os
import pytest
from sqlalchemy.orm import Session
from app.database import get_db, engine, Base, init_db
from app.models import Settings
from app.modules.settings.service import SettingsService
from app.modules.settings.schemas import SettingsUpdate


@pytest.fixture
def db():
    """Create a fresh database for each test."""
    os.makedirs("data", exist_ok=True)
    init_db()
    db = next(get_db())
    # Clean up any existing settings before test
    db.query(Settings).delete()
    db.commit()
    yield db
    # Clean up after test
    db.query(Settings).delete()
    db.commit()
    db.close()


def test_get_settings_empty(db):
    """Get settings when none configured."""
    service = SettingsService(db)
    response = service.get_settings()
    assert response.has_tmdb is False
    assert response.has_radarr is False


def test_update_and_get_settings(db):
    """Update settings and retrieve them."""
    service = SettingsService(db)
    update = SettingsUpdate(
        tmdb_api_key="test-tmdb-key-12345",
        radarr_url="http://localhost:7878",
        radarr_api_key="test-radarr-key",
    )
    service.update_settings(update)

    response = service.get_settings()
    assert response.has_tmdb is True
    assert response.has_radarr is True
    assert response.has_sonarr is False
    assert response.tmdb_api_key_masked == "***************2345"
    assert response.radarr_url == "http://localhost:7878"


def test_get_raw_value(db):
    """Get decrypted value for internal use."""
    service = SettingsService(db)
    update = SettingsUpdate(tmdb_api_key="my-secret-key")
    service.update_settings(update)

    raw = service.get_raw_value("tmdb_api_key")
    assert raw == "my-secret-key"


def test_get_raw_value_nonexistent(db):
    """Get raw value for key that doesn't exist."""
    service = SettingsService(db)
    raw = service.get_raw_value("nonexistent_key")
    assert raw is None
