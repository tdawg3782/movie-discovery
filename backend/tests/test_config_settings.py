"""Tests for config get_setting: DB precedence, error fallback, session cleanup."""
import logging
import os

import pytest
from cryptography.fernet import InvalidToken
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_setting, settings
from app.database import get_db, init_db
from app.models import Settings
from app.modules.settings.schemas import SettingsUpdate
from app.modules.settings.service import SettingsService


@pytest.fixture(autouse=True)
def setup_database():
    """Ensure database is initialized before tests."""
    os.makedirs("data", exist_ok=True)
    init_db()


@pytest.fixture
def db():
    """Create a fresh database session for each test (same pattern as settings service tests)."""
    os.makedirs("data", exist_ok=True)
    init_db()
    db = next(get_db())
    db.query(Settings).delete()
    db.commit()
    yield db
    db.query(Settings).delete()
    db.commit()
    db.close()


def test_get_setting_db_value_wins_over_env(db, monkeypatch):
    """(a) Precedence: a seeded DB value takes priority over the .env value."""
    service = SettingsService(db)
    service.update_settings(SettingsUpdate(radarr_url="http://db-radarr:7878"))
    monkeypatch.setattr(settings, "radarr_url", "http://env-radarr:9999")

    assert get_setting("radarr_url") == "http://db-radarr:7878"


def test_get_setting_db_error_falls_back_to_env_and_logs(monkeypatch, caplog):
    """(b) On DB error (InvalidToken) get_setting returns the env fallback and logs a warning."""
    def boom(self, key):
        raise InvalidToken()

    monkeypatch.setattr(SettingsService, "get_raw_value", boom)
    monkeypatch.setattr(settings, "tmdb_api_key", "env-fallback-key")

    with caplog.at_level(logging.WARNING):
        result = get_setting("tmdb_api_key")

    assert result == "env-fallback-key"
    assert any(
        rec.levelno == logging.WARNING and "tmdb_api_key" in rec.getMessage()
        for rec in caplog.records
    )


def test_get_setting_closes_session_on_error(monkeypatch):
    """(c) The session is closed on the error path (the finally always runs)."""
    closed = {"value": False}

    class FakeSession:
        def close(self) -> None:
            closed["value"] = True

    monkeypatch.setattr("app.database.SessionLocal", lambda: FakeSession())

    def boom(self, key):
        raise SQLAlchemyError("boom")

    monkeypatch.setattr(SettingsService, "get_raw_value", boom)

    # Should not raise; falls back to env (which may be None) and closes the fake session.
    get_setting("tmdb_api_key")

    assert closed["value"] is True
