# Settings & Config Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace .env file with UI-based configuration for API keys (TMDB, Radarr, Sonarr).

**Architecture:** New settings module with encrypted SQLite storage. Settings page in frontend with connection testing. Backward compatible - falls back to .env if no settings configured.

**Tech Stack:** FastAPI, SQLAlchemy, cryptography (Fernet), Vue 3, Pinia

---

## Task 1: Settings Database Model

**Files:**
- Modify: `backend/src/app/models.py`
- Modify: `backend/src/app/database.py`

**Step 1: Write the failing test**

Create `backend/tests/test_settings_model.py`:

```python
import pytest
from app.models import Settings
from app.database import get_db, engine
from sqlalchemy import inspect


def test_settings_table_exists():
    """Settings table should exist in database."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "settings" in tables


def test_settings_model_fields():
    """Settings model should have required fields."""
    assert hasattr(Settings, "id")
    assert hasattr(Settings, "key")
    assert hasattr(Settings, "value")
    assert hasattr(Settings, "encrypted")
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_settings_model.py -v`
Expected: FAIL with "cannot import name 'Settings'"

**Step 3: Write minimal implementation**

Add to `backend/src/app/models.py`:

```python
class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, nullable=False, index=True)
    value = Column(String, nullable=False)
    encrypted = Column(Boolean, default=False)
```

Update `backend/src/app/database.py` to create table:

```python
# After Base.metadata.create_all(bind=engine)
# (already handles all models)
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_settings_model.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/app/models.py backend/tests/test_settings_model.py
git commit -m "feat(settings): add Settings database model"
```

---

## Task 2: Settings Encryption Service

**Files:**
- Create: `backend/src/app/modules/settings/__init__.py`
- Create: `backend/src/app/modules/settings/encryption.py`
- Create: `backend/tests/test_settings_encryption.py`

**Step 1: Write the failing test**

Create `backend/tests/test_settings_encryption.py`:

```python
import pytest
from app.modules.settings.encryption import encrypt_value, decrypt_value, mask_value


def test_encrypt_decrypt_roundtrip():
    """Encrypted value should decrypt to original."""
    original = "my-secret-api-key-12345"
    encrypted = encrypt_value(original)
    decrypted = decrypt_value(encrypted)
    assert decrypted == original
    assert encrypted != original


def test_mask_value_shows_last_four():
    """Mask should show only last 4 characters."""
    value = "abcdefghijklmnop"
    masked = mask_value(value)
    assert masked == "************mnop"


def test_mask_short_value():
    """Short values should be fully masked."""
    value = "abc"
    masked = mask_value(value)
    assert masked == "***"
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_settings_encryption.py -v`
Expected: FAIL with "No module named 'app.modules.settings'"

**Step 3: Write minimal implementation**

Create `backend/src/app/modules/settings/__init__.py`:

```python
# Settings module
```

Create `backend/src/app/modules/settings/encryption.py`:

```python
import os
import base64
from cryptography.fernet import Fernet

# Generate or load encryption key
_KEY_FILE = os.path.join(os.path.dirname(__file__), ".encryption_key")


def _get_or_create_key() -> bytes:
    """Get existing key or create new one."""
    if os.path.exists(_KEY_FILE):
        with open(_KEY_FILE, "rb") as f:
            return f.read()
    key = Fernet.generate_key()
    with open(_KEY_FILE, "wb") as f:
        f.write(key)
    return key


_fernet = Fernet(_get_or_create_key())


def encrypt_value(value: str) -> str:
    """Encrypt a string value."""
    return _fernet.encrypt(value.encode()).decode()


def decrypt_value(encrypted: str) -> str:
    """Decrypt an encrypted string value."""
    return _fernet.decrypt(encrypted.encode()).decode()


def mask_value(value: str) -> str:
    """Mask a value, showing only last 4 characters."""
    if len(value) <= 4:
        return "*" * len(value)
    return "*" * (len(value) - 4) + value[-4:]
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_settings_encryption.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/app/modules/settings/
git add backend/tests/test_settings_encryption.py
git commit -m "feat(settings): add encryption service for API keys"
```

---

## Task 3: Settings Schemas

**Files:**
- Create: `backend/src/app/modules/settings/schemas.py`
- Create: `backend/tests/test_settings_schemas.py`

**Step 1: Write the failing test**

Create `backend/tests/test_settings_schemas.py`:

```python
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
    assert "masked" in data.model_fields


def test_connection_test_request():
    """ConnectionTestRequest should validate service type."""
    data = ConnectionTestRequest(service="tmdb")
    assert data.service == "tmdb"


def test_connection_test_response():
    """ConnectionTestResponse should have success and message."""
    data = ConnectionTestResponse(success=True, message="Connected!")
    assert data.success is True
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_settings_schemas.py -v`
Expected: FAIL with "cannot import name 'SettingsUpdate'"

**Step 3: Write minimal implementation**

Create `backend/src/app/modules/settings/schemas.py`:

```python
from typing import Optional, Literal
from pydantic import BaseModel, HttpUrl


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
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_settings_schemas.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/app/modules/settings/schemas.py
git add backend/tests/test_settings_schemas.py
git commit -m "feat(settings): add Pydantic schemas for settings API"
```

---

## Task 4: Settings Service

**Files:**
- Create: `backend/src/app/modules/settings/service.py`
- Create: `backend/tests/test_settings_service.py`

**Step 1: Write the failing test**

Create `backend/tests/test_settings_service.py`:

```python
import pytest
from sqlalchemy.orm import Session
from app.database import get_db, engine, Base
from app.models import Settings
from app.modules.settings.service import SettingsService
from app.modules.settings.schemas import SettingsUpdate


@pytest.fixture
def db():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    yield db
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
    assert response.tmdb_api_key_masked == "***********12345"
    assert response.radarr_url == "http://localhost:7878"


def test_get_raw_value(db):
    """Get decrypted value for internal use."""
    service = SettingsService(db)
    update = SettingsUpdate(tmdb_api_key="my-secret-key")
    service.update_settings(update)

    raw = service.get_raw_value("tmdb_api_key")
    assert raw == "my-secret-key"
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_settings_service.py -v`
Expected: FAIL with "cannot import name 'SettingsService'"

**Step 3: Write minimal implementation**

Create `backend/src/app/modules/settings/service.py`:

```python
from typing import Optional
from sqlalchemy.orm import Session
from app.models import Settings
from app.modules.settings.schemas import SettingsUpdate, SettingsResponse
from app.modules.settings.encryption import encrypt_value, decrypt_value, mask_value


# Keys that should be encrypted
ENCRYPTED_KEYS = {"tmdb_api_key", "radarr_api_key", "sonarr_api_key"}


class SettingsService:
    """Service for managing application settings."""

    def __init__(self, db: Session):
        self.db = db

    def get_settings(self) -> SettingsResponse:
        """Get all settings with masked sensitive values."""
        settings = {s.key: s for s in self.db.query(Settings).all()}

        return SettingsResponse(
            tmdb_api_key_masked=self._get_masked(settings, "tmdb_api_key"),
            radarr_url=self._get_plain(settings, "radarr_url"),
            radarr_api_key_masked=self._get_masked(settings, "radarr_api_key"),
            sonarr_url=self._get_plain(settings, "sonarr_url"),
            sonarr_api_key_masked=self._get_masked(settings, "sonarr_api_key"),
            has_tmdb="tmdb_api_key" in settings,
            has_radarr="radarr_url" in settings and "radarr_api_key" in settings,
            has_sonarr="sonarr_url" in settings and "sonarr_api_key" in settings,
        )

    def update_settings(self, update: SettingsUpdate) -> None:
        """Update settings from request."""
        for key, value in update.model_dump(exclude_none=True).items():
            self._set_value(key, value)
        self.db.commit()

    def get_raw_value(self, key: str) -> Optional[str]:
        """Get decrypted value for internal use."""
        setting = self.db.query(Settings).filter(Settings.key == key).first()
        if not setting:
            return None
        if setting.encrypted:
            return decrypt_value(setting.value)
        return setting.value

    def _get_masked(self, settings: dict, key: str) -> Optional[str]:
        """Get masked value for display."""
        if key not in settings:
            return None
        value = settings[key].value
        if settings[key].encrypted:
            value = decrypt_value(value)
        return mask_value(value)

    def _get_plain(self, settings: dict, key: str) -> Optional[str]:
        """Get plain value (for non-sensitive fields)."""
        if key not in settings:
            return None
        return settings[key].value

    def _set_value(self, key: str, value: str) -> None:
        """Set a setting value, encrypting if needed."""
        encrypted = key in ENCRYPTED_KEYS
        if encrypted:
            value = encrypt_value(value)

        setting = self.db.query(Settings).filter(Settings.key == key).first()
        if setting:
            setting.value = value
            setting.encrypted = encrypted
        else:
            setting = Settings(key=key, value=value, encrypted=encrypted)
            self.db.add(setting)
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_settings_service.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/app/modules/settings/service.py
git add backend/tests/test_settings_service.py
git commit -m "feat(settings): add settings service with encryption"
```

---

## Task 5: Settings Router

**Files:**
- Create: `backend/src/app/modules/settings/router.py`
- Create: `backend/tests/test_settings_router.py`
- Modify: `backend/src/app/main.py`

**Step 1: Write the failing test**

Create `backend/tests/test_settings_router.py`:

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_get_settings():
    """GET /api/settings should return settings."""
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert "has_tmdb" in data
    assert "has_radarr" in data
    assert "has_sonarr" in data


def test_update_settings():
    """PUT /api/settings should update settings."""
    response = client.put(
        "/api/settings",
        json={"tmdb_api_key": "test-key-for-router"}
    )
    assert response.status_code == 200

    # Verify it was saved
    response = client.get("/api/settings")
    data = response.json()
    assert data["has_tmdb"] is True


def test_test_connection_invalid_service():
    """POST /api/settings/test with invalid service should fail."""
    response = client.post(
        "/api/settings/test",
        json={"service": "invalid"}
    )
    assert response.status_code == 422
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_settings_router.py -v`
Expected: FAIL with 404 (route not found)

**Step 3: Write minimal implementation**

Create `backend/src/app/modules/settings/router.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import httpx

from app.database import get_db
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
        api_key = service.get_raw_value("tmdb_api_key")
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
        url = service.get_raw_value("radarr_url")
        api_key = service.get_raw_value("radarr_api_key")
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
        url = service.get_raw_value("sonarr_url")
        api_key = service.get_raw_value("sonarr_api_key")
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
```

Modify `backend/src/app/main.py` to include router:

```python
# Add import at top
from app.modules.settings.router import router as settings_router

# Add router registration (after other routers)
app.include_router(settings_router)
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_settings_router.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/app/modules/settings/router.py
git add backend/tests/test_settings_router.py
git add backend/src/app/main.py
git commit -m "feat(settings): add settings API router with connection testing"
```

---

## Task 6: Config Integration

**Files:**
- Modify: `backend/src/app/config.py`
- Create: `backend/tests/test_config_settings.py`

**Step 1: Write the failing test**

Create `backend/tests/test_config_settings.py`:

```python
import pytest
from app.config import get_setting


def test_get_setting_from_db():
    """get_setting should check database first."""
    # This will return None or env value if DB empty
    result = get_setting("tmdb_api_key")
    # Should not raise, returns value or None
    assert result is None or isinstance(result, str)
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_config_settings.py -v`
Expected: FAIL with "cannot import name 'get_setting'"

**Step 3: Write minimal implementation**

Modify `backend/src/app/config.py`:

```python
from typing import Optional
from functools import lru_cache
from pydantic_settings import BaseSettings
from pathlib import Path

# Find .env file in project root (parent of backend)
env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"


class Settings(BaseSettings):
    # Existing settings from .env (fallback)
    tmdb_api_key: str = ""
    radarr_url: str = ""
    radarr_api_key: str = ""
    sonarr_url: str = ""
    sonarr_api_key: str = ""
    database_path: str = "./data/movie_discovery.db"

    class Config:
        env_file = str(env_path)
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings():
    return Settings()


def get_setting(key: str) -> Optional[str]:
    """Get a setting value, checking database first, then .env fallback."""
    from app.database import SessionLocal
    from app.modules.settings.service import SettingsService

    try:
        db = SessionLocal()
        service = SettingsService(db)
        value = service.get_raw_value(key)
        db.close()
        if value:
            return value
    except Exception:
        pass

    # Fallback to .env
    settings = get_settings()
    return getattr(settings, key, None) or None
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_config_settings.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/app/config.py
git add backend/tests/test_config_settings.py
git commit -m "feat(settings): integrate settings DB with config fallback"
```

---

## Task 7: Frontend Settings Service

**Files:**
- Create: `frontend/src/services/settings.js`

**Step 1: Create the service**

Create `frontend/src/services/settings.js`:

```javascript
import api from './api'

export default {
  /**
   * Get current settings (with masked keys)
   */
  async getSettings() {
    const response = await api.get('/settings')
    return response
  },

  /**
   * Update settings
   * @param {Object} settings - Settings to update
   */
  async updateSettings(settings) {
    const response = await api.put('/settings', settings)
    return response
  },

  /**
   * Test connection to a service
   * @param {string} service - 'tmdb', 'radarr', or 'sonarr'
   */
  async testConnection(service) {
    const response = await api.post('/settings/test', { service })
    return response
  }
}
```

**Step 2: Commit**

```bash
git add frontend/src/services/settings.js
git commit -m "feat(settings): add frontend settings service"
```

---

## Task 8: Frontend Settings View

**Files:**
- Create: `frontend/src/views/SettingsView.vue`
- Modify: `frontend/src/router/index.js`

**Step 1: Create the Settings page**

Create `frontend/src/views/SettingsView.vue`:

```vue
<template>
  <div class="settings-view">
    <h1>Settings</h1>

    <div v-if="loading" class="loading">Loading settings...</div>

    <form v-else @submit.prevent="saveSettings" class="settings-form">
      <!-- TMDB Section -->
      <section class="settings-section">
        <h2>TMDB</h2>
        <div class="form-group">
          <label for="tmdb_api_key">API Key</label>
          <div class="input-with-action">
            <input
              id="tmdb_api_key"
              v-model="form.tmdb_api_key"
              :type="showKeys.tmdb ? 'text' : 'password'"
              :placeholder="settings.tmdb_api_key_masked || 'Enter TMDB API key'"
            />
            <button type="button" @click="showKeys.tmdb = !showKeys.tmdb" class="btn-icon">
              {{ showKeys.tmdb ? 'Hide' : 'Show' }}
            </button>
            <button type="button" @click="testConnection('tmdb')" :disabled="testing.tmdb" class="btn-test">
              {{ testing.tmdb ? 'Testing...' : 'Test' }}
            </button>
          </div>
          <div v-if="testResults.tmdb" :class="['test-result', testResults.tmdb.success ? 'success' : 'error']">
            {{ testResults.tmdb.message }}
          </div>
        </div>
      </section>

      <!-- Radarr Section -->
      <section class="settings-section">
        <h2>Radarr</h2>
        <div class="form-group">
          <label for="radarr_url">URL</label>
          <input
            id="radarr_url"
            v-model="form.radarr_url"
            type="url"
            :placeholder="settings.radarr_url || 'http://localhost:7878'"
          />
        </div>
        <div class="form-group">
          <label for="radarr_api_key">API Key</label>
          <div class="input-with-action">
            <input
              id="radarr_api_key"
              v-model="form.radarr_api_key"
              :type="showKeys.radarr ? 'text' : 'password'"
              :placeholder="settings.radarr_api_key_masked || 'Enter Radarr API key'"
            />
            <button type="button" @click="showKeys.radarr = !showKeys.radarr" class="btn-icon">
              {{ showKeys.radarr ? 'Hide' : 'Show' }}
            </button>
            <button type="button" @click="testConnection('radarr')" :disabled="testing.radarr" class="btn-test">
              {{ testing.radarr ? 'Testing...' : 'Test' }}
            </button>
          </div>
          <div v-if="testResults.radarr" :class="['test-result', testResults.radarr.success ? 'success' : 'error']">
            {{ testResults.radarr.message }}
          </div>
        </div>
      </section>

      <!-- Sonarr Section -->
      <section class="settings-section">
        <h2>Sonarr</h2>
        <div class="form-group">
          <label for="sonarr_url">URL</label>
          <input
            id="sonarr_url"
            v-model="form.sonarr_url"
            type="url"
            :placeholder="settings.sonarr_url || 'http://localhost:8989'"
          />
        </div>
        <div class="form-group">
          <label for="sonarr_api_key">API Key</label>
          <div class="input-with-action">
            <input
              id="sonarr_api_key"
              v-model="form.sonarr_api_key"
              :type="showKeys.sonarr ? 'text' : 'password'"
              :placeholder="settings.sonarr_api_key_masked || 'Enter Sonarr API key'"
            />
            <button type="button" @click="showKeys.sonarr = !showKeys.sonarr" class="btn-icon">
              {{ showKeys.sonarr ? 'Hide' : 'Show' }}
            </button>
            <button type="button" @click="testConnection('sonarr')" :disabled="testing.sonarr" class="btn-test">
              {{ testing.sonarr ? 'Testing...' : 'Test' }}
            </button>
          </div>
          <div v-if="testResults.sonarr" :class="['test-result', testResults.sonarr.success ? 'success' : 'error']">
            {{ testResults.sonarr.message }}
          </div>
        </div>
      </section>

      <!-- Save Button -->
      <div class="form-actions">
        <button type="submit" :disabled="saving" class="btn-save">
          {{ saving ? 'Saving...' : 'Save Settings' }}
        </button>
        <div v-if="saveMessage" :class="['save-message', saveSuccess ? 'success' : 'error']">
          {{ saveMessage }}
        </div>
      </div>
    </form>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import settingsService from '@/services/settings'

const loading = ref(true)
const saving = ref(false)
const saveMessage = ref('')
const saveSuccess = ref(false)

const settings = ref({})
const form = reactive({
  tmdb_api_key: '',
  radarr_url: '',
  radarr_api_key: '',
  sonarr_url: '',
  sonarr_api_key: ''
})

const showKeys = reactive({
  tmdb: false,
  radarr: false,
  sonarr: false
})

const testing = reactive({
  tmdb: false,
  radarr: false,
  sonarr: false
})

const testResults = reactive({
  tmdb: null,
  radarr: null,
  sonarr: null
})

onMounted(async () => {
  await loadSettings()
})

async function loadSettings() {
  try {
    settings.value = await settingsService.getSettings()
    // Pre-fill URLs (not keys, those stay masked)
    form.radarr_url = settings.value.radarr_url || ''
    form.sonarr_url = settings.value.sonarr_url || ''
  } catch (error) {
    console.error('Failed to load settings:', error)
  } finally {
    loading.value = false
  }
}

async function saveSettings() {
  saving.value = true
  saveMessage.value = ''

  try {
    // Only send non-empty values
    const updates = {}
    Object.entries(form).forEach(([key, value]) => {
      if (value && value.trim()) {
        updates[key] = value.trim()
      }
    })

    if (Object.keys(updates).length === 0) {
      saveMessage.value = 'No changes to save'
      saveSuccess.value = false
      return
    }

    settings.value = await settingsService.updateSettings(updates)
    saveMessage.value = 'Settings saved successfully'
    saveSuccess.value = true

    // Clear form fields (keys are now saved)
    form.tmdb_api_key = ''
    form.radarr_api_key = ''
    form.sonarr_api_key = ''
  } catch (error) {
    saveMessage.value = 'Failed to save settings'
    saveSuccess.value = false
    console.error('Failed to save settings:', error)
  } finally {
    saving.value = false
  }
}

async function testConnection(service) {
  testing[service] = true
  testResults[service] = null

  try {
    testResults[service] = await settingsService.testConnection(service)
  } catch (error) {
    testResults[service] = { success: false, message: 'Connection test failed' }
  } finally {
    testing[service] = false
  }
}
</script>

<style scoped>
.settings-view {
  max-width: 600px;
  margin: 0 auto;
  padding: 2rem;
}

h1 {
  margin-bottom: 2rem;
  color: #fff;
}

.settings-section {
  background: #1a1a2e;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
}

.settings-section h2 {
  margin: 0 0 1rem 0;
  color: #e94560;
  font-size: 1.2rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: #ccc;
}

.form-group input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #333;
  border-radius: 4px;
  background: #0f0f1a;
  color: #fff;
  font-size: 1rem;
}

.input-with-action {
  display: flex;
  gap: 0.5rem;
}

.input-with-action input {
  flex: 1;
}

.btn-icon, .btn-test {
  padding: 0.75rem 1rem;
  border: 1px solid #333;
  border-radius: 4px;
  background: #252540;
  color: #fff;
  cursor: pointer;
  white-space: nowrap;
}

.btn-icon:hover, .btn-test:hover {
  background: #333355;
}

.btn-test:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.test-result {
  margin-top: 0.5rem;
  padding: 0.5rem;
  border-radius: 4px;
  font-size: 0.9rem;
}

.test-result.success {
  background: rgba(0, 200, 83, 0.2);
  color: #00c853;
}

.test-result.error {
  background: rgba(233, 69, 96, 0.2);
  color: #e94560;
}

.form-actions {
  margin-top: 2rem;
}

.btn-save {
  width: 100%;
  padding: 1rem;
  border: none;
  border-radius: 4px;
  background: #e94560;
  color: #fff;
  font-size: 1rem;
  cursor: pointer;
}

.btn-save:hover {
  background: #d63850;
}

.btn-save:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.save-message {
  margin-top: 1rem;
  padding: 0.75rem;
  border-radius: 4px;
  text-align: center;
}

.save-message.success {
  background: rgba(0, 200, 83, 0.2);
  color: #00c853;
}

.save-message.error {
  background: rgba(233, 69, 96, 0.2);
  color: #e94560;
}

.loading {
  text-align: center;
  color: #ccc;
  padding: 2rem;
}
</style>
```

**Step 2: Add route**

Modify `frontend/src/router/index.js`:

```javascript
// Add import
import SettingsView from '@/views/SettingsView.vue'

// Add route to routes array
{
  path: '/settings',
  name: 'Settings',
  component: SettingsView
}
```

**Step 3: Commit**

```bash
git add frontend/src/views/SettingsView.vue
git add frontend/src/router/index.js
git commit -m "feat(settings): add settings page with connection testing UI"
```

---

## Task 9: Navigation Update

**Files:**
- Modify: `frontend/src/App.vue` (or navigation component)

**Step 1: Add settings link to navigation**

Add settings icon/link to navigation bar:

```vue
<!-- Add to nav -->
<router-link to="/settings" class="nav-link" title="Settings">
  <span class="settings-icon">⚙️</span>
</router-link>
```

**Step 2: Commit**

```bash
git add frontend/src/App.vue
git commit -m "feat(settings): add settings link to navigation"
```

---

## Task 10: Final Integration Test

**Files:**
- None (manual testing)

**Step 1: Run all backend tests**

```bash
cd backend && pytest -v
```
Expected: All tests pass

**Step 2: Start servers and test manually**

```bash
# From worktree root
start.bat
```

1. Navigate to http://localhost:3000/settings
2. Enter test API keys
3. Click "Test" for each service
4. Click "Save Settings"
5. Refresh page - verify masked keys appear
6. Navigate to Discover - verify it still works

**Step 3: Final commit**

```bash
git add -A
git commit -m "feat(settings): complete settings module with UI and API"
```

---

## Summary

| Task | Description |
|------|-------------|
| 1 | Settings database model |
| 2 | Encryption service |
| 3 | Pydantic schemas |
| 4 | Settings service |
| 5 | API router |
| 6 | Config integration |
| 7 | Frontend service |
| 8 | Settings view |
| 9 | Navigation update |
| 10 | Integration testing |
