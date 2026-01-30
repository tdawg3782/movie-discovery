# Season Selection Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Allow users to select specific seasons when adding TV shows to watchlist, and pass that selection to Sonarr.

**Architecture:** Add `selected_seasons` JSON column to watchlist table. Update API to accept/return season selection. Create modal component for season selection. Modify Sonarr client to set per-season monitoring.

**Tech Stack:** Python/FastAPI, SQLite/SQLAlchemy, Vue 3 Composition API, Pydantic

---

## Task 1: Database Migration - Add selected_seasons Column

**Files:**
- Modify: `backend/src/app/models.py:36-50`

**Step 1: Add the column to the Watchlist model**

In `backend/src/app/models.py`, add after line 46 (after `status`):

```python
selected_seasons: Mapped[str | None] = mapped_column(Text, nullable=True)
# JSON array like "[1, 2, 3]" or null for all seasons
```

**Step 2: Run database migration**

```bash
cd backend
python -c "
import sqlite3
conn = sqlite3.connect('data/movie_discovery.db')
cur = conn.cursor()
cur.execute('ALTER TABLE watchlist ADD COLUMN selected_seasons TEXT')
conn.commit()
print('Column added successfully')
conn.close()
"
```

Expected: `Column added successfully`

**Step 3: Verify migration**

```bash
cd backend
python -c "
import sqlite3
conn = sqlite3.connect('data/movie_discovery.db')
cur = conn.cursor()
cur.execute('PRAGMA table_info(watchlist)')
columns = [row[1] for row in cur.fetchall()]
print('Columns:', columns)
assert 'selected_seasons' in columns, 'Migration failed'
print('Migration verified!')
conn.close()
"
```

Expected: Shows columns including `selected_seasons`, prints `Migration verified!`

**Step 4: Commit**

```bash
git add backend/src/app/models.py
git commit -m "feat(db): add selected_seasons column to watchlist table"
```

---

## Task 2: Backend Schemas - Update WatchlistAdd and WatchlistItem

**Files:**
- Modify: `backend/src/app/schemas.py:37-58`
- Test: `backend/tests/test_watchlist_schemas.py` (create)

**Step 1: Write failing test**

Create `backend/tests/test_watchlist_schemas.py`:

```python
"""Tests for watchlist schemas with season selection."""
import pytest
from app.schemas import WatchlistAdd, WatchlistItem
from datetime import datetime


def test_watchlist_add_with_seasons():
    """WatchlistAdd accepts selected_seasons."""
    data = WatchlistAdd(
        tmdb_id=12345,
        media_type="show",
        selected_seasons=[1, 2, 3]
    )
    assert data.selected_seasons == [1, 2, 3]


def test_watchlist_add_without_seasons():
    """WatchlistAdd works without selected_seasons (defaults to None)."""
    data = WatchlistAdd(tmdb_id=12345, media_type="show")
    assert data.selected_seasons is None


def test_watchlist_item_with_seasons():
    """WatchlistItem includes selected_seasons and total_seasons."""
    item = WatchlistItem(
        id=1,
        tmdb_id=12345,
        media_type="show",
        title="Test Show",
        added_at=datetime.now(),
        selected_seasons=[1, 2],
        total_seasons=5
    )
    assert item.selected_seasons == [1, 2]
    assert item.total_seasons == 5
```

**Step 2: Run test to verify it fails**

```bash
cd backend
python -m pytest tests/test_watchlist_schemas.py -v
```

Expected: FAIL - `selected_seasons` field not recognized

**Step 3: Update schemas**

In `backend/src/app/schemas.py`, modify `WatchlistAdd` (around line 37):

```python
class WatchlistAdd(BaseModel):
    """Request to add item to watchlist."""

    tmdb_id: int
    media_type: str
    notes: str | None = None
    selected_seasons: list[int] | None = None  # None = all seasons
```

Modify `WatchlistItem` (around line 45):

```python
class WatchlistItem(MediaBase):
    """Watchlist item response."""

    id: int
    added_at: datetime
    notes: str | None = None
    status: str = "pending"  # pending, added, downloading
    selected_seasons: list[int] | None = None  # None = all seasons
    total_seasons: int | None = None  # For display: "X of Y seasons"
```

**Step 4: Run test to verify it passes**

```bash
cd backend
python -m pytest tests/test_watchlist_schemas.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/app/schemas.py backend/tests/test_watchlist_schemas.py
git commit -m "feat(api): add selected_seasons to watchlist schemas"
```

---

## Task 3: Backend Service - Update Watchlist Service

**Files:**
- Modify: `backend/src/app/modules/watchlist/service.py:16-30`
- Test: `backend/tests/test_watchlist_service.py` (create)

**Step 1: Write failing test**

Create `backend/tests/test_watchlist_service.py`:

```python
"""Tests for watchlist service with season selection."""
import pytest
import json
from unittest.mock import MagicMock
from app.modules.watchlist.service import WatchlistService
from app.models import Watchlist


def test_add_with_selected_seasons():
    """Service stores selected_seasons as JSON."""
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None

    service = WatchlistService(mock_db)

    # Call add with selected_seasons
    service.add(tmdb_id=12345, media_type="show", selected_seasons=[1, 2, 3])

    # Verify the Watchlist object was created with JSON seasons
    mock_db.add.assert_called_once()
    added_item = mock_db.add.call_args[0][0]
    assert added_item.selected_seasons == "[1, 2, 3]"


def test_add_without_seasons_stores_null():
    """Service stores None when no seasons specified."""
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None

    service = WatchlistService(mock_db)
    service.add(tmdb_id=12345, media_type="show")

    added_item = mock_db.add.call_args[0][0]
    assert added_item.selected_seasons is None
```

**Step 2: Run test to verify it fails**

```bash
cd backend
python -m pytest tests/test_watchlist_service.py -v
```

Expected: FAIL - `selected_seasons` parameter not accepted

**Step 3: Update service**

In `backend/src/app/modules/watchlist/service.py`, modify the `add` method:

```python
import json

# ... existing code ...

def add(
    self,
    tmdb_id: int,
    media_type: str,
    notes: str | None = None,
    selected_seasons: list[int] | None = None
) -> Watchlist:
    """Add item to watchlist. Returns existing if duplicate."""
    existing = (
        self.db.query(Watchlist)
        .filter(Watchlist.tmdb_id == tmdb_id, Watchlist.media_type == media_type)
        .first()
    )
    if existing:
        return existing

    # Convert seasons list to JSON string for storage
    seasons_json = json.dumps(selected_seasons) if selected_seasons else None

    item = Watchlist(
        tmdb_id=tmdb_id,
        media_type=media_type,
        notes=notes,
        selected_seasons=seasons_json
    )
    self.db.add(item)
    self.db.commit()
    self.db.refresh(item)
    return item
```

**Step 4: Run test to verify it passes**

```bash
cd backend
python -m pytest tests/test_watchlist_service.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/app/modules/watchlist/service.py backend/tests/test_watchlist_service.py
git commit -m "feat(service): store selected_seasons as JSON in watchlist"
```

---

## Task 4: Backend Router - Update Watchlist Endpoints

**Files:**
- Modify: `backend/src/app/modules/watchlist/router.py`

**Step 1: Update add_to_watchlist endpoint**

In `backend/src/app/modules/watchlist/router.py`, modify the `add_to_watchlist` function to pass `selected_seasons`:

Find line with `item = service.add(` and update to:

```python
item = service.add(
    tmdb_id=data.tmdb_id,
    media_type=data.media_type,
    notes=data.notes,
    selected_seasons=data.selected_seasons
)
```

**Step 2: Update the response to include selected_seasons**

In both `get_watchlist` and `add_to_watchlist`, update the WatchlistItem construction.

Add import at top:
```python
import json
```

In the `enrich_item` function inside `get_watchlist`, add after getting details:

```python
# Parse selected_seasons from JSON
selected_seasons = None
if item.selected_seasons:
    selected_seasons = json.loads(item.selected_seasons)

# Get total seasons from TMDB (only for shows)
total_seasons = None
if item.media_type == "show":
    total_seasons = details.get("number_of_seasons")
```

Then include in WatchlistItem:
```python
selected_seasons=selected_seasons,
total_seasons=total_seasons,
```

**Step 3: Test manually**

```bash
cd backend
python -c "
import httpx
import asyncio

async def test():
    async with httpx.AsyncClient(timeout=30) as client:
        # Add with seasons
        resp = await client.post(
            'http://localhost:3000/api/watchlist',
            json={'tmdb_id': 94997, 'media_type': 'show', 'selected_seasons': [1, 2]}
        )
        print('Add response:', resp.status_code)
        data = resp.json()
        print('selected_seasons:', data.get('selected_seasons'))
        print('total_seasons:', data.get('total_seasons'))

asyncio.run(test())
"
```

Expected: Shows `selected_seasons: [1, 2]` and `total_seasons` with a number

**Step 4: Commit**

```bash
git add backend/src/app/modules/watchlist/router.py
git commit -m "feat(api): handle selected_seasons in watchlist endpoints"
```

---

## Task 5: Backend - Update Watchlist Seasons Endpoint

**Files:**
- Modify: `backend/src/app/modules/watchlist/router.py`
- Modify: `backend/src/app/modules/watchlist/service.py`

**Step 1: Add update method to service**

In `backend/src/app/modules/watchlist/service.py`, add method:

```python
def update_seasons(self, tmdb_id: int, selected_seasons: list[int] | None) -> Watchlist | None:
    """Update selected seasons for a watchlist item."""
    item = self.get_by_tmdb_id(tmdb_id)
    if not item:
        return None

    item.selected_seasons = json.dumps(selected_seasons) if selected_seasons else None
    self.db.commit()
    self.db.refresh(item)
    return item
```

**Step 2: Add PATCH endpoint to router**

In `backend/src/app/modules/watchlist/router.py`, add new schema and endpoint:

Add to imports at top:
```python
from pydantic import BaseModel
```

Add schema class (after other imports):
```python
class UpdateSeasonsRequest(BaseModel):
    selected_seasons: list[int] | None
```

Add endpoint (before the parameterized delete endpoint):
```python
@router.patch("/{tmdb_id}/seasons")
async def update_watchlist_seasons(
    tmdb_id: int,
    data: UpdateSeasonsRequest,
    service: WatchlistService = Depends(get_service)
):
    """Update selected seasons for a watchlist item."""
    item = service.update_seasons(tmdb_id, data.selected_seasons)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    selected_seasons = None
    if item.selected_seasons:
        selected_seasons = json.loads(item.selected_seasons)

    return {"success": True, "selected_seasons": selected_seasons}
```

**Step 3: Test manually**

```bash
cd backend
python -c "
import httpx
import asyncio

async def test():
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.patch(
            'http://localhost:3000/api/watchlist/94997/seasons',
            json={'selected_seasons': [1, 3, 5]}
        )
        print('Update response:', resp.status_code, resp.json())

asyncio.run(test())
"
```

**Step 4: Commit**

```bash
git add backend/src/app/modules/watchlist/router.py backend/src/app/modules/watchlist/service.py
git commit -m "feat(api): add endpoint to update watchlist seasons"
```

---

## Task 6: Backend - Update Sonarr Client for Season Selection

**Files:**
- Modify: `backend/src/app/modules/sonarr/client.py:52-87`
- Test: `backend/tests/test_sonarr_seasons.py` (create)

**Step 1: Write failing test**

Create `backend/tests/test_sonarr_seasons.py`:

```python
"""Tests for Sonarr client season selection."""
import pytest
from unittest.mock import AsyncMock, patch
from app.modules.sonarr.client import SonarrClient


@pytest.mark.asyncio
async def test_add_series_with_selected_seasons():
    """Sonarr client sets season monitoring based on selection."""
    client = SonarrClient(url="http://test:8989", api_key="test")

    mock_series = {
        "title": "Test Show",
        "tvdbId": 12345,
        "seasons": [
            {"seasonNumber": 0, "monitored": False},
            {"seasonNumber": 1, "monitored": True},
            {"seasonNumber": 2, "monitored": True},
            {"seasonNumber": 3, "monitored": True},
        ]
    }

    with patch.object(client, 'lookup_series', new_callable=AsyncMock) as mock_lookup, \
         patch.object(client, 'get_series_by_tvdb_id', new_callable=AsyncMock) as mock_get, \
         patch.object(client, '_get', new_callable=AsyncMock) as mock_get_api, \
         patch.object(client, '_post', new_callable=AsyncMock) as mock_post:

        mock_lookup.return_value = mock_series.copy()
        mock_get.return_value = None  # Not already in library
        mock_get_api.side_effect = [
            [{"path": "/tv"}],  # root folders
            [{"id": 1}]  # quality profiles
        ]
        mock_post.return_value = {"id": 1, "title": "Test Show"}

        await client.add_series(tmdb_id=12345, selected_seasons=[1, 3])

        # Verify the posted data has correct season monitoring
        posted_data = mock_post.call_args[0][1]
        seasons = {s["seasonNumber"]: s["monitored"] for s in posted_data["seasons"]}

        assert seasons[0] == False  # Specials never monitored
        assert seasons[1] == True   # Selected
        assert seasons[2] == False  # Not selected
        assert seasons[3] == True   # Selected
```

**Step 2: Run test to verify it fails**

```bash
cd backend
python -m pytest tests/test_sonarr_seasons.py -v
```

Expected: FAIL - `selected_seasons` parameter not accepted

**Step 3: Update SonarrClient.add_series**

In `backend/src/app/modules/sonarr/client.py`, modify `add_series`:

```python
async def add_series(
    self,
    tmdb_id: int,
    quality_profile_id: int | None = None,
    root_folder_path: str | None = None,
    selected_seasons: list[int] | None = None,
) -> dict:
    """Add series to Sonarr.

    Args:
        tmdb_id: TMDB series ID
        quality_profile_id: Quality profile to use
        root_folder_path: Root folder path
        selected_seasons: List of season numbers to monitor (None = all)
    """
    # Check if already in library
    series = await self.lookup_series(tmdb_id)
    if series and series.get("tvdbId"):
        existing = await self.get_series_by_tvdb_id(series["tvdbId"])
        if existing:
            raise ValueError(f"Series already in Sonarr library: {existing.get('title', tmdb_id)}")

    if not series:
        raise ValueError(f"Series not found: {tmdb_id}")

    if not root_folder_path:
        folders = await self._get("/rootfolder")
        if not folders:
            raise ValueError("No root folders configured in Sonarr")
        root_folder_path = folders[0]["path"]

    # Get quality profile if not specified
    if not quality_profile_id:
        profiles = await self.get_quality_profiles()
        if not profiles:
            raise ValueError("No quality profiles configured in Sonarr")
        quality_profile_id = profiles[0]["id"]

    # Set season monitoring based on selection
    if selected_seasons is not None:
        for season in series.get("seasons", []):
            season_num = season.get("seasonNumber", 0)
            # Only monitor if in selected list (never auto-monitor specials/season 0)
            season["monitored"] = season_num in selected_seasons and season_num > 0

    series["qualityProfileId"] = quality_profile_id
    series["rootFolderPath"] = root_folder_path
    series["monitored"] = True
    series["addOptions"] = {"searchForMissingEpisodes": True}

    return await self._post("/series", series)
```

**Step 4: Run test to verify it passes**

```bash
cd backend
python -m pytest tests/test_sonarr_seasons.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/app/modules/sonarr/client.py backend/tests/test_sonarr_seasons.py
git commit -m "feat(sonarr): support selected_seasons in add_series"
```

---

## Task 7: Backend - Update Watchlist Process to Pass Seasons

**Files:**
- Modify: `backend/src/app/modules/watchlist/service.py`

**Step 1: Update process_batch to read and pass seasons**

In `backend/src/app/modules/watchlist/service.py`, modify `process_batch`:

```python
async def process_batch(
    self, tmdb_ids: list[int], media_type: str
) -> tuple[list[int], list[dict]]:
    """
    Process watchlist items by sending to Radarr/Sonarr.
    Returns (processed_ids, failed_items).
    """
    processed = []
    failed = []

    for tmdb_id in tmdb_ids:
        try:
            item = self.get_by_tmdb_id(tmdb_id)
            selected_seasons = None
            if item and item.selected_seasons:
                selected_seasons = json.loads(item.selected_seasons)

            if media_type == "movie":
                client = RadarrClient(settings.radarr_url, settings.radarr_api_key)
                await client.add_movie(tmdb_id)
            else:
                client = SonarrClient(settings.sonarr_url, settings.sonarr_api_key)
                await client.add_series(tmdb_id, selected_seasons=selected_seasons)

            processed.append(tmdb_id)

            # Update watchlist item status
            if item:
                item.status = "added"
                self.db.commit()

        except Exception as e:
            failed.append({"tmdb_id": tmdb_id, "error": str(e)})

    return processed, failed
```

**Step 2: Run existing tests to ensure no regression**

```bash
cd backend
python -m pytest tests/ -v --tb=short
```

Expected: All tests pass (or pre-existing failures only)

**Step 3: Commit**

```bash
git add backend/src/app/modules/watchlist/service.py
git commit -m "feat(watchlist): pass selected_seasons when processing to Sonarr"
```

---

## Task 8: Frontend - Add Watchlist Service Methods

**Files:**
- Modify: `frontend/src/services/watchlist.js`

**Step 1: Add updateSeasons method**

In `frontend/src/services/watchlist.js`:

```javascript
import api from './api'

export const watchlistService = {
  getAll: () => api.get('/watchlist'),

  add: (tmdbId, mediaType, notes = null, selectedSeasons = null) =>
    api.post('/watchlist', {
      tmdb_id: tmdbId,
      media_type: mediaType,
      notes,
      selected_seasons: selectedSeasons
    }),

  remove: (id) => api.delete(`/watchlist/${id}`),

  updateSeasons: (tmdbId, selectedSeasons) =>
    api.patch(`/watchlist/${tmdbId}/seasons`, { selected_seasons: selectedSeasons }),

  processItems: (ids, mediaType) =>
    api.post('/watchlist/process', { ids, media_type: mediaType }),

  deleteItems: (ids) =>
    api.delete('/watchlist/batch', { data: { ids } }),
}
```

**Step 2: Commit**

```bash
git add frontend/src/services/watchlist.js
git commit -m "feat(frontend): add updateSeasons to watchlist service"
```

---

## Task 9: Frontend - Create SeasonSelectModal Component

**Files:**
- Create: `frontend/src/components/SeasonSelectModal.vue`

**Step 1: Create the modal component**

Create `frontend/src/components/SeasonSelectModal.vue`:

```vue
<template>
  <div v-if="isOpen" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal">
      <div class="modal-header">
        <h2>Add to Watchlist</h2>
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
          <label class="season-item select-all">
            <input
              type="checkbox"
              :checked="allSelected"
              :indeterminate.prop="someSelected && !allSelected"
              @change="toggleAll"
            />
            <span>Select All</span>
          </label>

          <label
            v-for="season in filteredSeasons"
            :key="season.season_number"
            class="season-item"
          >
            <input
              type="checkbox"
              :checked="isSelected(season.season_number)"
              @change="toggleSeason(season.season_number)"
            />
            <span>Season {{ season.season_number }}</span>
            <span class="episode-count">({{ season.episode_count }} episodes)</span>
          </label>
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn-cancel" @click="$emit('close')">Cancel</button>
        <button
          class="btn-add"
          @click="handleAdd"
          :disabled="selectedSeasons.length === 0 || adding"
        >
          {{ adding ? 'Adding...' : 'Add to Watchlist' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  isOpen: { type: Boolean, default: false },
  show: { type: Object, required: true }
})

const emit = defineEmits(['close', 'add'])

const loading = ref(false)
const adding = ref(false)
const selectedSeasons = ref([])

// Filter out season 0 (specials)
const filteredSeasons = computed(() =>
  (props.show.seasons || []).filter(s => s.season_number > 0)
)

const releaseYear = computed(() => {
  const date = props.show.first_air_date
  return date ? new Date(date).getFullYear() : ''
})

const allSelected = computed(() =>
  filteredSeasons.value.length > 0 &&
  filteredSeasons.value.every(s => selectedSeasons.value.includes(s.season_number))
)

const someSelected = computed(() =>
  selectedSeasons.value.length > 0
)

// Initialize with all seasons selected when modal opens
watch(() => props.isOpen, (open) => {
  if (open) {
    selectedSeasons.value = filteredSeasons.value.map(s => s.season_number)
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
    selectedSeasons.value = filteredSeasons.value.map(s => s.season_number)
  }
}

async function handleAdd() {
  adding.value = true
  try {
    emit('add', selectedSeasons.value)
  } finally {
    adding.value = false
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: #1a1a2e;
  border-radius: 12px;
  width: 90%;
  max-width: 400px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid #333;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.25rem;
  color: #fff;
}

.close-btn {
  background: none;
  border: none;
  color: #888;
  font-size: 1.5rem;
  cursor: pointer;
}

.close-btn:hover {
  color: #fff;
}

.modal-body {
  padding: 1.5rem;
  overflow-y: auto;
  flex: 1;
}

.show-info {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.poster {
  width: 60px;
  border-radius: 4px;
}

.show-info h3 {
  margin: 0 0 0.25rem 0;
  color: #fff;
}

.year {
  color: #888;
  margin: 0;
}

.loading {
  color: #888;
  text-align: center;
  padding: 2rem;
}

.seasons-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.season-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  background: #252540;
  border-radius: 6px;
  cursor: pointer;
  color: #fff;
}

.season-item:hover {
  background: #333355;
}

.season-item.select-all {
  background: #1a1a2e;
  border: 1px solid #333;
  margin-bottom: 0.5rem;
}

.season-item input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.episode-count {
  color: #888;
  margin-left: auto;
  font-size: 0.9rem;
}

.modal-footer {
  display: flex;
  gap: 1rem;
  padding: 1rem 1.5rem;
  border-top: 1px solid #333;
}

.btn-cancel, .btn-add {
  flex: 1;
  padding: 0.75rem;
  border-radius: 6px;
  font-size: 1rem;
  cursor: pointer;
  border: none;
}

.btn-cancel {
  background: #333;
  color: #fff;
}

.btn-cancel:hover {
  background: #444;
}

.btn-add {
  background: #e94560;
  color: #fff;
}

.btn-add:hover:not(:disabled) {
  background: #d63850;
}

.btn-add:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
```

**Step 2: Commit**

```bash
git add frontend/src/components/SeasonSelectModal.vue
git commit -m "feat(ui): create SeasonSelectModal component"
```

---

## Task 10: Frontend - Update MediaDetailView for Season Selection

**Files:**
- Modify: `frontend/src/views/MediaDetailView.vue`

**Step 1: Import and add modal**

In `frontend/src/views/MediaDetailView.vue`:

Add import:
```javascript
import SeasonSelectModal from '@/components/SeasonSelectModal.vue'
```

Add state:
```javascript
const showSeasonModal = ref(false)
```

Add modal to template (after TrailerModal):
```vue
<!-- Season Select Modal (TV shows only) -->
<SeasonSelectModal
  :is-open="showSeasonModal"
  :show="media"
  @close="showSeasonModal = false"
  @add="handleAddWithSeasons"
/>
```

**Step 2: Update addToWatchlist function**

Replace the `addToWatchlist` function:

```javascript
async function addToWatchlist() {
  if (addingToWatchlist.value || addedToWatchlist.value) return

  // For TV shows, open season selector modal
  if (mediaType.value === 'tv') {
    showSeasonModal.value = true
    return
  }

  // For movies, add directly
  addingToWatchlist.value = true
  try {
    await watchlistService.add(mediaId.value, 'movie')
    addedToWatchlist.value = true
  } catch (error) {
    console.error('Failed to add to watchlist:', error)
  } finally {
    addingToWatchlist.value = false
  }
}

async function handleAddWithSeasons(selectedSeasons) {
  addingToWatchlist.value = true
  try {
    await watchlistService.add(mediaId.value, 'show', null, selectedSeasons)
    addedToWatchlist.value = true
    showSeasonModal.value = false
  } catch (error) {
    console.error('Failed to add to watchlist:', error)
  } finally {
    addingToWatchlist.value = false
  }
}
```

**Step 3: Test manually**

1. Navigate to a TV show detail page
2. Click "Add to Watchlist"
3. Verify modal opens with seasons
4. Select/deselect seasons
5. Click "Add to Watchlist" in modal
6. Verify it saves

**Step 4: Commit**

```bash
git add frontend/src/views/MediaDetailView.vue
git commit -m "feat(ui): show season selector modal for TV shows"
```

---

## Task 11: Frontend - Update WatchlistView with Expandable Rows

**Files:**
- Modify: `frontend/src/views/WatchlistView.vue`

**Step 1: Add expand/collapse state and season editing**

This is a larger change. Key modifications:

1. Add `expandedItem` ref to track which item is expanded
2. Add click handler to toggle expansion
3. Add season checkboxes in expanded view
4. Add save handler for season changes

The full implementation requires modifying the template and script. Due to size, implement incrementally:

**Step 1a: Add state variables**

```javascript
const expandedItem = ref(null)
const savingSeasons = ref(false)
```

**Step 1b: Add toggle function**

```javascript
function toggleExpand(item) {
  if (item.media_type !== 'show') return
  expandedItem.value = expandedItem.value === item.tmdb_id ? null : item.tmdb_id
}

function isExpanded(tmdbId) {
  return expandedItem.value === tmdbId
}
```

**Step 1c: Add season update function**

```javascript
async function updateSeasons(tmdbId, selectedSeasons) {
  savingSeasons.value = true
  try {
    await watchlistService.updateSeasons(tmdbId, selectedSeasons)
    // Refresh watchlist to get updated data
    await loadWatchlist()
  } catch (error) {
    console.error('Failed to update seasons:', error)
  } finally {
    savingSeasons.value = false
  }
}
```

**Step 1d: Update template for expandable rows**

Add to the item row a click handler and expansion indicator:
```vue
@click="toggleExpand(item)"
:class="{ expandable: item.media_type === 'show', expanded: isExpanded(item.tmdb_id) }"
```

Add season display after the main row content (inside the item loop):
```vue
<div v-if="isExpanded(item.tmdb_id)" class="season-editor">
  <!-- Season checkboxes here -->
</div>
```

**Step 2: Test manually**

1. Go to Watchlist page
2. Click on a TV show row
3. Verify it expands to show seasons
4. Toggle seasons and save
5. Verify changes persist

**Step 3: Commit**

```bash
git add frontend/src/views/WatchlistView.vue
git commit -m "feat(ui): add expandable season editing to watchlist"
```

---

## Task 12: Final Testing and Cleanup

**Step 1: Run all backend tests**

```bash
cd backend
python -m pytest tests/ -v
```

**Step 2: Manual end-to-end test**

1. Add a TV show from discover page → modal should appear
2. Select specific seasons → add to watchlist
3. Go to watchlist → verify seasons shown
4. Expand and edit seasons → save
5. Process to Sonarr → verify only selected seasons monitored

**Step 3: Final commit**

```bash
git add -A
git commit -m "feat: complete season selection feature

- Add selected_seasons to watchlist database and API
- Create SeasonSelectModal for TV show add flow
- Add expandable season editing in WatchlistView
- Pass season selection to Sonarr when processing

Closes #season-selection"
```

---

## Summary

| Task | Component | Description |
|------|-----------|-------------|
| 1 | Database | Add `selected_seasons` column |
| 2 | Schemas | Update WatchlistAdd/Item |
| 3 | Service | Store seasons as JSON |
| 4 | Router | Handle seasons in endpoints |
| 5 | Router | Add PATCH endpoint for seasons |
| 6 | Sonarr | Pass seasons to add_series |
| 7 | Service | Read seasons in process_batch |
| 8 | Frontend | Update watchlist service |
| 9 | Frontend | Create SeasonSelectModal |
| 10 | Frontend | Update MediaDetailView |
| 11 | Frontend | Update WatchlistView |
| 12 | Testing | End-to-end verification |
