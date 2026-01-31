# Manage Seasons Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Allow users to add additional seasons to shows already in Sonarr, and filter Discovery by library status.

**Architecture:** Extend Sonarr client with season detail and update methods. Modify SeasonSelectModal to show status. Add library filter to FilterPanel. Route watchlist batch processing through update vs add paths.

**Tech Stack:** Python/FastAPI backend, Vue 3 frontend, Sonarr API v3

---

## Task 1: Sonarr Client - Get Series Details

**Files:**
- Modify: `backend/src/app/modules/sonarr/client.py`
- Create: `backend/tests/test_sonarr_season_details.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_sonarr_season_details.py
"""Tests for Sonarr season details."""
import pytest
from unittest.mock import AsyncMock, patch
from app.modules.sonarr.client import SonarrClient


@pytest.fixture
def client():
    return SonarrClient(url="http://localhost:8989", api_key="test_key")


@pytest.mark.asyncio
async def test_get_series_details_returns_season_status(client):
    """Get series details with season-level status."""
    mock_lookup = [{"tvdbId": 81189, "title": "Breaking Bad"}]
    mock_series = {
        "id": 1,
        "title": "Breaking Bad",
        "tvdbId": 81189,
        "seasons": [
            {"seasonNumber": 1, "monitored": True, "statistics": {"percentOfEpisodes": 100, "episodeCount": 7, "episodeFileCount": 7}},
            {"seasonNumber": 2, "monitored": True, "statistics": {"percentOfEpisodes": 50, "episodeCount": 13, "episodeFileCount": 6}},
            {"seasonNumber": 3, "monitored": False, "statistics": {"percentOfEpisodes": 0, "episodeCount": 13, "episodeFileCount": 0}},
        ]
    }

    with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = [mock_lookup, [mock_series]]
        result = await client.get_series_details(tmdb_id=1396)

    assert result is not None
    assert result["in_library"] is True
    assert result["sonarr_id"] == 1
    assert len(result["seasons"]) == 3
    assert result["seasons"][0]["status"] == "downloaded"
    assert result["seasons"][1]["status"] == "monitored"
    assert result["seasons"][2]["status"] == "available"


@pytest.mark.asyncio
async def test_get_series_details_not_in_library(client):
    """Returns None when series not in Sonarr library."""
    mock_lookup = [{"tvdbId": 81189, "title": "Breaking Bad"}]

    with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = [mock_lookup, []]  # Empty library result
        result = await client.get_series_details(tmdb_id=1396)

    assert result is None
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_sonarr_season_details.py -v`
Expected: FAIL with "AttributeError: 'SonarrClient' object has no attribute 'get_series_details'"

**Step 3: Write minimal implementation**

Add to `backend/src/app/modules/sonarr/client.py` after the `get_series_by_tvdb_id` method:

```python
async def get_series_details(self, tmdb_id: int) -> dict | None:
    """Get series details with season-level status from Sonarr library.

    Returns:
        {
            "in_library": True,
            "sonarr_id": 123,
            "title": "Breaking Bad",
            "seasons": [
                {"number": 1, "status": "downloaded", "episodes": "7/7", "episode_count": 7, "episode_file_count": 7},
                {"number": 2, "status": "monitored", "episodes": "6/13", "episode_count": 13, "episode_file_count": 6},
                {"number": 3, "status": "available", "episodes": "0/13", "episode_count": 13, "episode_file_count": 0},
            ]
        }
        Or None if not in library.
    """
    # Get TVDB ID from TMDB ID
    series = await self.lookup_series(tmdb_id)
    if not series or not series.get("tvdbId"):
        return None

    # Check if in library
    existing = await self.get_series_by_tvdb_id(series["tvdbId"])
    if not existing:
        return None

    # Transform seasons to our format
    seasons = []
    for season in existing.get("seasons", []):
        season_num = season.get("seasonNumber", 0)
        if season_num == 0:  # Skip specials
            continue

        stats = season.get("statistics", {})
        episode_count = stats.get("episodeCount", 0)
        episode_file_count = stats.get("episodeFileCount", 0)
        percent = stats.get("percentOfEpisodes", 0)

        # Determine status
        if percent == 100:
            status = "downloaded"
        elif season.get("monitored", False):
            status = "monitored"
        else:
            status = "available"

        seasons.append({
            "number": season_num,
            "status": status,
            "episodes": f"{episode_file_count}/{episode_count}",
            "episode_count": episode_count,
            "episode_file_count": episode_file_count,
        })

    return {
        "in_library": True,
        "sonarr_id": existing.get("id"),
        "title": existing.get("title"),
        "seasons": sorted(seasons, key=lambda s: s["number"]),
    }
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_sonarr_season_details.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/app/modules/sonarr/client.py backend/tests/test_sonarr_season_details.py
git commit -m "feat(sonarr): add get_series_details for season status"
```

---

## Task 2: Sonarr Client - Update Season Monitoring

**Files:**
- Modify: `backend/src/app/modules/sonarr/client.py`
- Modify: `backend/tests/test_sonarr_season_details.py`

**Step 1: Write the failing test**

Add to `backend/tests/test_sonarr_season_details.py`:

```python
@pytest.mark.asyncio
async def test_update_season_monitoring(client):
    """Update monitoring for additional seasons."""
    mock_lookup = [{"tvdbId": 81189}]
    mock_existing = {
        "id": 1,
        "title": "Breaking Bad",
        "tvdbId": 81189,
        "seasons": [
            {"seasonNumber": 1, "monitored": True},
            {"seasonNumber": 2, "monitored": False},
            {"seasonNumber": 3, "monitored": False},
        ]
    }
    mock_updated = {**mock_existing, "seasons": [
        {"seasonNumber": 1, "monitored": True},
        {"seasonNumber": 2, "monitored": True},  # Now monitored
        {"seasonNumber": 3, "monitored": False},
    ]}

    with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
        with patch.object(client, "_put", new_callable=AsyncMock) as mock_put:
            with patch.object(client, "_post", new_callable=AsyncMock) as mock_post:
                mock_get.side_effect = [mock_lookup, [mock_existing]]
                mock_put.return_value = mock_updated
                mock_post.return_value = {"id": 123}  # Command response

                result = await client.update_season_monitoring(tmdb_id=1396, seasons_to_add=[2])

    assert result["seasons"][1]["monitored"] is True
    mock_put.assert_called_once()
    mock_post.assert_called_once()  # Search command
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_sonarr_season_details.py::test_update_season_monitoring -v`
Expected: FAIL with "AttributeError: 'SonarrClient' object has no attribute 'update_season_monitoring'"

**Step 3: Write minimal implementation**

Add `_put` method and `update_season_monitoring` to `backend/src/app/modules/sonarr/client.py`:

```python
async def _put(self, endpoint: str, data: dict) -> Any:
    """Make PUT request to Sonarr API."""
    headers = {"X-Api-Key": self.api_key}
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        response = await client.put(
            f"{self.url}/api/v3{endpoint}",
            headers=headers,
            json=data,
        )
        response.raise_for_status()
        return response.json()

async def update_season_monitoring(self, tmdb_id: int, seasons_to_add: list[int]) -> dict:
    """Add monitoring for additional seasons and trigger search.

    Args:
        tmdb_id: TMDB ID of the series
        seasons_to_add: List of season numbers to start monitoring

    Returns:
        Updated series data from Sonarr
    """
    # Get TVDB ID
    series = await self.lookup_series(tmdb_id)
    if not series or not series.get("tvdbId"):
        raise ValueError(f"Series not found: {tmdb_id}")

    # Get existing series from library
    existing = await self.get_series_by_tvdb_id(series["tvdbId"])
    if not existing:
        raise ValueError(f"Series not in Sonarr library: {tmdb_id}")

    # Update season monitoring
    for season in existing.get("seasons", []):
        if season.get("seasonNumber") in seasons_to_add:
            season["monitored"] = True

    # PUT updated series
    updated = await self._put(f"/series/{existing['id']}", existing)

    # Trigger search for newly monitored seasons
    await self._post("/command", {
        "name": "SeriesSearch",
        "seriesId": existing["id"]
    })

    return updated
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_sonarr_season_details.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/app/modules/sonarr/client.py backend/tests/test_sonarr_season_details.py
git commit -m "feat(sonarr): add update_season_monitoring method"
```

---

## Task 3: API Endpoint - Season Status

**Files:**
- Modify: `backend/src/app/modules/sonarr/router.py`
- Create: `backend/tests/test_sonarr_seasons_endpoint.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_sonarr_seasons_endpoint.py
"""Tests for Sonarr seasons endpoint."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_sonarr_client():
    with patch("app.modules.sonarr.router.get_sonarr_client") as mock:
        mock_client = MagicMock()
        mock.return_value = mock_client
        yield mock_client


def test_get_series_seasons(client, mock_sonarr_client):
    """Get season status for a series."""
    mock_sonarr_client.get_series_details = AsyncMock(return_value={
        "in_library": True,
        "sonarr_id": 1,
        "title": "Breaking Bad",
        "seasons": [
            {"number": 1, "status": "downloaded", "episodes": "7/7"},
            {"number": 2, "status": "available", "episodes": "0/13"},
        ]
    })

    response = client.get("/api/sonarr/series/1396/seasons")

    assert response.status_code == 200
    data = response.json()
    assert data["in_library"] is True
    assert len(data["seasons"]) == 2


def test_get_series_seasons_not_in_library(client, mock_sonarr_client):
    """Returns 404 when series not in library."""
    mock_sonarr_client.get_series_details = AsyncMock(return_value=None)

    response = client.get("/api/sonarr/series/99999/seasons")

    assert response.status_code == 404
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_sonarr_seasons_endpoint.py -v`
Expected: FAIL with 404 (endpoint doesn't exist)

**Step 3: Write minimal implementation**

Add to `backend/src/app/modules/sonarr/router.py`:

```python
@router.get("/series/{tmdb_id}/seasons")
async def get_series_seasons(
    tmdb_id: int = Path(gt=0, description="TMDB series ID"),
    client: SonarrClient = Depends(get_sonarr_client),
):
    """Get season-level status for a series in Sonarr library."""
    result = await client.get_series_details(tmdb_id)
    if not result:
        raise HTTPException(status_code=404, detail="Series not in Sonarr library")
    return result
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_sonarr_seasons_endpoint.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/app/modules/sonarr/router.py backend/tests/test_sonarr_seasons_endpoint.py
git commit -m "feat(api): add GET /api/sonarr/series/{tmdb_id}/seasons endpoint"
```

---

## Task 4: Watchlist Model - Add is_season_update Field

**Files:**
- Modify: `backend/src/app/models.py`
- Create: `backend/tests/test_watchlist_season_update.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_watchlist_season_update.py
"""Tests for watchlist season update field."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import Watchlist


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_watchlist_has_is_season_update_field(db):
    """Watchlist model has is_season_update field."""
    item = Watchlist(
        tmdb_id=1396,
        media_type="tv",
        selected_seasons="[4, 5]",
        is_season_update=True
    )
    db.add(item)
    db.commit()

    result = db.query(Watchlist).filter_by(tmdb_id=1396).first()
    assert result.is_season_update is True


def test_watchlist_is_season_update_defaults_false(db):
    """is_season_update defaults to False."""
    item = Watchlist(tmdb_id=1234, media_type="tv")
    db.add(item)
    db.commit()

    result = db.query(Watchlist).filter_by(tmdb_id=1234).first()
    assert result.is_season_update is False
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_watchlist_season_update.py -v`
Expected: FAIL with "TypeError: Watchlist() got unexpected keyword argument 'is_season_update'"

**Step 3: Write minimal implementation**

Modify `backend/src/app/models.py`, add to Watchlist class:

```python
is_season_update: Mapped[bool] = mapped_column(Boolean, default=False)
# True when adding seasons to existing show in Sonarr
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_watchlist_season_update.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/app/models.py backend/tests/test_watchlist_season_update.py
git commit -m "feat(model): add is_season_update field to Watchlist"
```

---

## Task 5: Watchlist Service - Handle Season Updates in Batch Process

**Files:**
- Modify: `backend/src/app/modules/watchlist/service.py`
- Modify: `backend/tests/test_watchlist_batch.py`

**Step 1: Write the failing test**

Add to `backend/tests/test_watchlist_batch.py`:

```python
@pytest.mark.asyncio
async def test_batch_process_season_update(db):
    """Batch process routes season updates to update_season_monitoring."""
    # Add item with is_season_update=True
    item = Watchlist(
        tmdb_id=1396,
        media_type="tv",
        selected_seasons="[4, 5]",
        is_season_update=True
    )
    db.add(item)
    db.commit()

    service = WatchlistService(db)

    with patch("app.modules.watchlist.service.SonarrClient") as MockClient:
        mock_instance = MockClient.return_value
        mock_instance.update_season_monitoring = AsyncMock(return_value={"id": 1})

        with patch("app.modules.watchlist.service.settings") as mock_settings:
            mock_settings.sonarr_url = "http://localhost:8989"
            mock_settings.sonarr_api_key = "test"

            with patch("app.modules.watchlist.service.get_setting", return_value=None):
                processed, failed = await service.batch_process([1396], "tv")

    assert 1396 in processed
    mock_instance.update_season_monitoring.assert_called_once_with(1396, [4, 5])
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_watchlist_batch.py::test_batch_process_season_update -v`
Expected: FAIL (update_season_monitoring not called)

**Step 3: Write minimal implementation**

Modify `backend/src/app/modules/watchlist/service.py` batch_process method:

```python
# In the TV show processing section, replace:
await client.add_series(tmdb_id, root_folder_path=root_folder, selected_seasons=selected_seasons)

# With:
if item and item.is_season_update:
    # Update existing show's season monitoring
    await client.update_season_monitoring(tmdb_id, selected_seasons)
else:
    # Add new show
    await client.add_series(tmdb_id, root_folder_path=root_folder, selected_seasons=selected_seasons)
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_watchlist_batch.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/app/modules/watchlist/service.py backend/tests/test_watchlist_batch.py
git commit -m "feat(watchlist): route season updates through update_season_monitoring"
```

---

## Task 6: Watchlist API - Accept is_season_update

**Files:**
- Modify: `backend/src/app/modules/watchlist/schemas.py`
- Modify: `backend/src/app/modules/watchlist/service.py`

**Step 1: Write the failing test**

Add to existing watchlist router tests:

```python
def test_add_to_watchlist_with_is_season_update(client, db):
    """Add to watchlist with is_season_update flag."""
    response = client.post("/api/watchlist", json={
        "tmdb_id": 1396,
        "media_type": "tv",
        "selected_seasons": [4, 5],
        "is_season_update": True
    })

    assert response.status_code == 200
    item = db.query(Watchlist).filter_by(tmdb_id=1396).first()
    assert item.is_season_update is True
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_watchlist_router.py::test_add_to_watchlist_with_is_season_update -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Modify `backend/src/app/modules/watchlist/schemas.py`:

```python
class WatchlistAdd(BaseModel):
    tmdb_id: int
    media_type: str
    selected_seasons: list[int] | None = None
    is_season_update: bool = False  # Add this line
```

Modify `backend/src/app/modules/watchlist/service.py` `add_to_watchlist` method to pass through the field:

```python
def add_to_watchlist(self, data: WatchlistAdd) -> Watchlist:
    # ... existing code ...
    item = Watchlist(
        tmdb_id=data.tmdb_id,
        media_type=data.media_type,
        selected_seasons=json.dumps(data.selected_seasons) if data.selected_seasons else None,
        is_season_update=data.is_season_update,  # Add this line
    )
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_watchlist_router.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/app/modules/watchlist/schemas.py backend/src/app/modules/watchlist/service.py
git commit -m "feat(watchlist): accept is_season_update in add endpoint"
```

---

## Task 7: Frontend Service - Add Season APIs

**Files:**
- Modify: `frontend/src/services/api.js` (if needed)
- Create: `frontend/src/services/sonarr.js`

**Step 1: Create Sonarr service**

```javascript
// frontend/src/services/sonarr.js
import api from './api'

export default {
  /**
   * Get season status for a series in Sonarr
   * @param {number} tmdbId - TMDB ID of the series
   * @returns {Promise<{in_library: boolean, sonarr_id: number, seasons: Array}>}
   */
  async getSeriesSeasons(tmdbId) {
    return await api.get(`/sonarr/series/${tmdbId}/seasons`)
  }
}
```

**Step 2: Commit**

```bash
git add frontend/src/services/sonarr.js
git commit -m "feat(frontend): add Sonarr service for season APIs"
```

---

## Task 8: Frontend - SeasonSelectModal with Status Display

**Files:**
- Modify: `frontend/src/components/SeasonSelectModal.vue`

**Step 1: Update SeasonSelectModal**

Replace the entire component with updated version that:
- Accepts `existingSeasons` prop (from Sonarr)
- Shows color-coded status
- Disables downloaded/monitored seasons
- Changes button text for updates

```vue
<template>
  <div v-if="isOpen" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal">
      <div class="modal-header">
        <h2>{{ isUpdate ? 'Add More Seasons' : 'Add to Watchlist' }}</h2>
        <button class="close-btn" @click="$emit('close')">&times;</button>
      </div>

      <div class="modal-body">
        <div class="show-info">
          <img
            v-if="show.poster_path"
            :src="`https://image.tmdb.org/t/p/w92${show.poster_path}`"
            :alt="show.name"
            class="poster"
          />
          <div>
            <h3>{{ show.name || show.title }}</h3>
            <p class="year">{{ releaseYear }}</p>
          </div>
        </div>

        <div v-if="loading" class="loading">Loading seasons...</div>

        <div v-else class="seasons-list">
          <label v-if="availableSeasons.length > 0" class="season-item select-all">
            <input
              type="checkbox"
              :checked="allSelected"
              :indeterminate.prop="someSelected && !allSelected"
              @change="toggleAll"
            />
            <span>Select All Available</span>
          </label>

          <div
            v-for="season in displaySeasons"
            :key="season.number"
            :class="['season-item', season.status]"
          >
            <input
              v-if="season.status === 'available'"
              type="checkbox"
              :checked="isSelected(season.number)"
              @change="toggleSeason(season.number)"
            />
            <span class="status-indicator" :class="season.status"></span>
            <span>Season {{ season.number }}</span>
            <span class="episode-count">
              <template v-if="season.episodes">({{ season.episodes }})</template>
              <template v-else>({{ season.episode_count }} episodes)</template>
            </span>
          </div>

          <div v-if="availableSeasons.length === 0 && isUpdate" class="no-seasons">
            All seasons are already monitored or downloaded.
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn-cancel" @click="$emit('close')">Cancel</button>
        <button
          class="btn-add"
          @click="handleAdd"
          :disabled="selectedSeasons.length === 0 || adding"
        >
          {{ adding ? 'Adding...' : buttonText }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  isOpen: { type: Boolean, default: false },
  show: { type: Object, required: true },
  existingSeasons: { type: Array, default: null } // From Sonarr if already in library
})

const emit = defineEmits(['close', 'add'])

const loading = ref(false)
const adding = ref(false)
const selectedSeasons = ref([])

// Check if this is an update (show already in Sonarr)
const isUpdate = computed(() => props.existingSeasons !== null)

// Combine TMDB seasons with Sonarr status
const displaySeasons = computed(() => {
  const tmdbSeasons = (props.show.seasons || []).filter(s => s.season_number > 0)

  if (!props.existingSeasons) {
    // New show - all seasons available
    return tmdbSeasons.map(s => ({
      number: s.season_number,
      status: 'available',
      episode_count: s.episode_count
    }))
  }

  // Existing show - merge with Sonarr status
  return tmdbSeasons.map(s => {
    const sonarrSeason = props.existingSeasons.find(es => es.number === s.season_number)
    return {
      number: s.season_number,
      status: sonarrSeason?.status || 'available',
      episodes: sonarrSeason?.episodes,
      episode_count: s.episode_count
    }
  })
})

const availableSeasons = computed(() =>
  displaySeasons.value.filter(s => s.status === 'available')
)

const releaseYear = computed(() => {
  const date = props.show.first_air_date
  return date ? new Date(date).getFullYear() : ''
})

const allSelected = computed(() =>
  availableSeasons.value.length > 0 &&
  availableSeasons.value.every(s => selectedSeasons.value.includes(s.number))
)

const someSelected = computed(() => selectedSeasons.value.length > 0)

const buttonText = computed(() => {
  const count = selectedSeasons.value.length
  if (isUpdate.value) {
    return count === 0 ? 'Select Seasons' : `Add ${count} Season${count > 1 ? 's' : ''}`
  }
  return 'Add to Watchlist'
})

// Initialize selection when modal opens
watch(() => props.isOpen, (open) => {
  if (open) {
    if (isUpdate.value) {
      // For updates, start with nothing selected
      selectedSeasons.value = []
    } else {
      // For new shows, select all
      selectedSeasons.value = availableSeasons.value.map(s => s.number)
    }
  }
})

function isSelected(seasonNumber) {
  return selectedSeasons.value.includes(seasonNumber)
}

function toggleSeason(seasonNumber) {
  const index = selectedSeasons.value.indexOf(seasonNumber)
  if (index === -1) {
    selectedSeasons.value.push(seasonNumber)
  } else {
    selectedSeasons.value.splice(index, 1)
  }
}

function toggleAll() {
  if (allSelected.value) {
    selectedSeasons.value = []
  } else {
    selectedSeasons.value = availableSeasons.value.map(s => s.number)
  }
}

async function handleAdd() {
  adding.value = true
  try {
    emit('add', {
      seasons: selectedSeasons.value,
      isUpdate: isUpdate.value
    })
  } finally {
    adding.value = false
  }
}
</script>

<style scoped>
/* ... existing styles ... */

.status-indicator {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-indicator.downloaded {
  background: #4ade80;
}

.status-indicator.monitored {
  background: #fbbf24;
}

.status-indicator.available {
  background: #6b7280;
}

.season-item.downloaded,
.season-item.monitored {
  opacity: 0.6;
  cursor: default;
}

.season-item.downloaded:hover,
.season-item.monitored:hover {
  background: #252540;
}

.no-seasons {
  text-align: center;
  color: #888;
  padding: 2rem;
}
</style>
```

**Step 2: Commit**

```bash
git add frontend/src/components/SeasonSelectModal.vue
git commit -m "feat(ui): SeasonSelectModal shows status for existing shows"
```

---

## Task 9: Frontend - MediaDetailView Integration

**Files:**
- Modify: `frontend/src/views/MediaDetailView.vue`

**Step 1: Update MediaDetailView**

Add logic to:
1. Fetch season status when viewing a TV show
2. Pass `existingSeasons` to SeasonSelectModal
3. Handle the updated `add` event with `isUpdate` flag

Key changes:

```javascript
import sonarrService from '@/services/sonarr'

// Add ref for existing seasons
const existingSeasons = ref(null)

// Fetch season status for TV shows
async function checkLibraryStatus() {
  if (media.value.media_type === 'tv' || route.params.type === 'tv') {
    try {
      const details = await sonarrService.getSeriesSeasons(media.value.id)
      if (details?.in_library) {
        existingSeasons.value = details.seasons
      }
    } catch (e) {
      // Not in library, that's fine
      existingSeasons.value = null
    }
  }
}

// Update handleAddSeasons to pass isUpdate
async function handleAddSeasons({ seasons, isUpdate }) {
  await watchlistService.addToWatchlist({
    tmdb_id: media.value.id,
    media_type: 'tv',
    selected_seasons: seasons,
    is_season_update: isUpdate
  })
  // ... rest of handler
}
```

**Step 2: Commit**

```bash
git add frontend/src/views/MediaDetailView.vue
git commit -m "feat(ui): MediaDetailView fetches season status for existing shows"
```

---

## Task 10: Frontend - FilterPanel Library Status

**Files:**
- Modify: `frontend/src/components/FilterPanel.vue`

**Step 1: Add Library Status filter section**

Add after existing filter groups:

```vue
<!-- Library Status Filter -->
<div class="filter-group">
  <label>Library Status</label>
  <div class="checkbox-group">
    <label class="checkbox-item">
      <input
        type="checkbox"
        v-model="filters.inLibrary"
      />
      <span>{{ mediaType === 'movie' ? 'In Radarr' : 'In Sonarr' }}</span>
    </label>
    <label class="checkbox-item">
      <input
        type="checkbox"
        v-model="filters.notInLibrary"
      />
      <span>Not in Library</span>
    </label>
  </div>
</div>
```

Add to reactive filters:

```javascript
const filters = reactive({
  // ... existing filters ...
  inLibrary: false,
  notInLibrary: false,
})
```

Update `applyFilters`:

```javascript
function applyFilters() {
  emit('filter-change', {
    // ... existing filters ...
    inLibrary: filters.inLibrary,
    notInLibrary: filters.notInLibrary,
  })
}
```

**Step 2: Commit**

```bash
git add frontend/src/components/FilterPanel.vue
git commit -m "feat(ui): add Library Status filter to FilterPanel"
```

---

## Task 11: Frontend - DiscoverView Library Filtering

**Files:**
- Modify: `frontend/src/views/DiscoverView.vue`

**Step 1: Add library status filtering logic**

```javascript
import radarrService from '@/services/radarr' // Create if needed
import sonarrService from '@/services/sonarr'

// After fetching results, filter by library status
async function applyLibraryFilter(items, filters, mediaType) {
  if (!filters.inLibrary && !filters.notInLibrary) {
    return items // No filter applied
  }

  const tmdbIds = items.map(i => i.id)
  let statuses = {}

  if (mediaType === 'movie') {
    statuses = await radarrService.getBatchStatus(tmdbIds)
  } else {
    statuses = await sonarrService.getBatchStatus(tmdbIds)
  }

  return items.filter(item => {
    const inLib = statuses[item.id] != null
    if (filters.inLibrary && !filters.notInLibrary) return inLib
    if (filters.notInLibrary && !filters.inLibrary) return !inLib
    return true // Both checked = show all
  })
}
```

**Step 2: Commit**

```bash
git add frontend/src/views/DiscoverView.vue
git commit -m "feat(ui): DiscoverView filters by library status"
```

---

## Task 12: Frontend - WatchlistView Display Updates

**Files:**
- Modify: `frontend/src/views/WatchlistView.vue`

**Step 1: Update display for season update items**

```vue
<span class="seasons-info" v-if="item.selected_seasons">
  <template v-if="item.is_season_update">
    +Seasons {{ formatSeasons(item.selected_seasons) }}
  </template>
  <template v-else>
    Seasons {{ formatSeasons(item.selected_seasons) }}
  </template>
</span>
```

Add CSS for visual distinction:

```css
.seasons-info {
  color: #888;
  font-size: 0.85rem;
}

/* Highlight update items */
.watchlist-item.is-update .seasons-info {
  color: #4ade80;
}
```

**Step 2: Commit**

```bash
git add frontend/src/views/WatchlistView.vue
git commit -m "feat(ui): WatchlistView shows +Seasons for update items"
```

---

## Final Task: Integration Test

**Step 1: Run all tests**

```bash
cd backend && python -m pytest -v
```

**Step 2: Manual test flow**

1. Add a TV show with only Season 1
2. Process it to Sonarr
3. View the show again in Discovery
4. Click "+" - should show Season 1 as green (downloaded/monitored)
5. Select Seasons 2, 3
6. Check watchlist - should show "+Seasons 2, 3"
7. Process - should update Sonarr monitoring

**Step 3: Final commit**

```bash
git add -A
git commit -m "feat: complete manage seasons for existing shows feature"
```
