"""Tests for the shared external-client factory (DB-first creds, persistent pools)."""
import os

import httpx
import pytest
import respx

import app.modules.clients as clients_module
from app.modules.clients import (
    get_radarr_client,
    get_sonarr_client,
    get_tmdb_client,
)
from app.database import get_db, init_db
from app.models import Settings
from app.modules.settings.service import SettingsService
from app.modules.settings.schemas import SettingsUpdate


@pytest.fixture
def db():
    """Create a fresh settings DB for each test (same harness as test_settings_service)."""
    os.makedirs("data", exist_ok=True)
    init_db()
    db = next(get_db())
    db.query(Settings).delete()
    db.commit()
    yield db
    db.query(Settings).delete()
    db.commit()
    db.close()


@pytest.fixture(autouse=True)
def reset_client_cache():
    """Module globals persist across tests; reset them so each test starts clean."""
    yield
    clients_module._radarr_client = None
    clients_module._sonarr_client = None
    clients_module.tmdb_client.api_key = ""


async def test_radarr_uses_db_credentials(db):
    """DB-saved radarr_url/api_key win over env defaults."""
    SettingsService(db).update_settings(
        SettingsUpdate(radarr_url="http://db-radarr:7878", radarr_api_key="db-radarr-key")
    )

    client = await get_radarr_client()

    assert client.url == "http://db-radarr:7878"
    assert client.api_key == "db-radarr-key"


async def test_sonarr_uses_db_credentials(db):
    """DB-saved sonarr_url/api_key win over env defaults."""
    SettingsService(db).update_settings(
        SettingsUpdate(sonarr_url="http://db-sonarr:8989", sonarr_api_key="db-sonarr-key")
    )

    client = await get_sonarr_client()

    assert client.url == "http://db-sonarr:8989"
    assert client.api_key == "db-sonarr-key"


async def test_radarr_same_instance_when_unchanged(db):
    """Unchanged creds -> the same persistent client instance is reused (M7)."""
    SettingsService(db).update_settings(
        SettingsUpdate(radarr_url="http://db-radarr:7878", radarr_api_key="db-radarr-key")
    )

    first = await get_radarr_client()
    second = await get_radarr_client()

    assert first is second


async def test_radarr_new_instance_on_credential_change_closes_old(db):
    """Changing the saved api_key swaps in a new client and closes the old pool."""
    service = SettingsService(db)
    service.update_settings(
        SettingsUpdate(radarr_url="http://db-radarr:7878", radarr_api_key="db-radarr-key")
    )

    old = await get_radarr_client()
    # Force a live httpx pool so we can prove close() ran.
    await old._get_client()
    assert old._client is not None

    service.update_settings(SettingsUpdate(radarr_api_key="rotated-key"))

    new = await get_radarr_client()

    assert new is not old
    assert new.api_key == "rotated-key"
    assert old._client is None  # old pool was awaited closed during the swap

    await new.close()


async def test_radarr_db_settings_reach_the_wire(db):
    """DB url + key are actually used by the httpx call (TG2)."""
    SettingsService(db).update_settings(
        SettingsUpdate(radarr_url="http://db-radarr:7878", radarr_api_key="db-radarr-key")
    )

    with respx.mock:
        route = respx.get("http://db-radarr:7878/api/v3/system/status").mock(
            return_value=httpx.Response(200, json={})
        )
        client = await get_radarr_client()
        await client._get("/system/status")
        assert route.called

        await client.close()


async def test_tmdb_refreshes_and_is_singleton(db):
    """get_tmdb_client refreshes api_key from DB and always returns the same instance."""
    SettingsService(db).update_settings(SettingsUpdate(tmdb_api_key="db-tmdb-key"))

    first = get_tmdb_client()
    second = get_tmdb_client()

    assert first is second
    assert first.api_key == "db-tmdb-key"
