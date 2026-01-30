# Watchlist Workflow Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform watchlist into a staging queue where items are reviewed before being sent to Radarr/Sonarr.

**Architecture:** Modify existing watchlist to support batch processing. Change "Add" button behavior on discovery page. Add batch selection and processing UI to watchlist.

**Tech Stack:** FastAPI, SQLAlchemy, Vue 3, Pinia

---

## Task 1: Batch Processing Endpoint

**Files:**
- Modify: `backend/src/app/modules/watchlist/router.py`
- Modify: `backend/src/app/modules/watchlist/service.py`
- Create: `backend/src/app/modules/watchlist/schemas.py`
- Create: `backend/tests/test_watchlist_batch.py`

**Step 1: Write the failing test**

Create `backend/tests/test_watchlist_batch.py`:

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db, Base, engine
from app.models import Watchlist


client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    """Setup test database."""
    Base.metadata.create_all(bind=engine)
    yield
    db = next(get_db())
    db.query(Watchlist).delete()
    db.commit()


def test_batch_process_movies():
    """POST /api/watchlist/process should send items to Radarr/Sonarr."""
    # First add items to watchlist
    client.post("/api/watchlist", json={
        "tmdb_id": 603,
        "media_type": "movie",
        "title": "The Matrix",
        "poster_path": "/test.jpg"
    })
    client.post("/api/watchlist", json={
        "tmdb_id": 604,
        "media_type": "movie",
        "title": "The Matrix Reloaded",
        "poster_path": "/test2.jpg"
    })

    # Process batch
    response = client.post("/api/watchlist/process", json={
        "ids": [603, 604],
        "media_type": "movie"
    })
    assert response.status_code == 200
    data = response.json()
    assert "processed" in data
    assert "failed" in data


def test_batch_delete():
    """DELETE /api/watchlist/batch should remove multiple items."""
    # Add items
    client.post("/api/watchlist", json={
        "tmdb_id": 100,
        "media_type": "movie",
        "title": "Test 1"
    })
    client.post("/api/watchlist", json={
        "tmdb_id": 101,
        "media_type": "movie",
        "title": "Test 2"
    })

    # Delete batch
    response = client.request(
        "DELETE",
        "/api/watchlist/batch",
        json={"ids": [100, 101]}
    )
    assert response.status_code == 200

    # Verify deletion
    response = client.get("/api/watchlist")
    assert len(response.json()) == 0
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_watchlist_batch.py -v`
Expected: FAIL with 404 or 405

**Step 3: Write minimal implementation**

Create `backend/src/app/modules/watchlist/schemas.py`:

```python
from typing import List, Literal
from pydantic import BaseModel


class BatchProcessRequest(BaseModel):
    """Request to process multiple watchlist items."""
    ids: List[int]  # TMDB IDs
    media_type: Literal["movie", "tv"]


class BatchProcessResponse(BaseModel):
    """Response from batch processing."""
    processed: List[int]  # Successfully processed TMDB IDs
    failed: List[dict]  # Failed items with error messages


class BatchDeleteRequest(BaseModel):
    """Request to delete multiple watchlist items."""
    ids: List[int]  # TMDB IDs
```

Add to `backend/src/app/modules/watchlist/service.py`:

```python
from typing import List, Tuple
from app.modules.radarr.client import RadarrClient
from app.modules.sonarr.client import SonarrClient


async def process_batch(
    self,
    tmdb_ids: List[int],
    media_type: str
) -> Tuple[List[int], List[dict]]:
    """
    Process watchlist items by sending to Radarr/Sonarr.
    Returns (processed_ids, failed_items).
    """
    processed = []
    failed = []

    for tmdb_id in tmdb_ids:
        try:
            if media_type == "movie":
                client = RadarrClient()
                await client.add_movie(tmdb_id)
            else:
                client = SonarrClient()
                await client.add_show(tmdb_id)

            processed.append(tmdb_id)

            # Update watchlist item status
            item = self.db.query(Watchlist).filter(
                Watchlist.tmdb_id == tmdb_id
            ).first()
            if item:
                item.status = "added"
                self.db.commit()

        except Exception as e:
            failed.append({
                "tmdb_id": tmdb_id,
                "error": str(e)
            })

    return processed, failed


def delete_batch(self, tmdb_ids: List[int]) -> int:
    """Delete multiple watchlist items. Returns count deleted."""
    deleted = self.db.query(Watchlist).filter(
        Watchlist.tmdb_id.in_(tmdb_ids)
    ).delete(synchronize_session=False)
    self.db.commit()
    return deleted
```

Add to `backend/src/app/modules/watchlist/router.py`:

```python
from app.modules.watchlist.schemas import (
    BatchProcessRequest,
    BatchProcessResponse,
    BatchDeleteRequest
)


@router.post("/process", response_model=BatchProcessResponse)
async def process_watchlist_items(
    request: BatchProcessRequest,
    db: Session = Depends(get_db)
):
    """Process watchlist items by sending to Radarr/Sonarr."""
    service = WatchlistService(db)
    processed, failed = await service.process_batch(
        request.ids,
        request.media_type
    )
    return BatchProcessResponse(processed=processed, failed=failed)


@router.delete("/batch")
async def delete_watchlist_items(
    request: BatchDeleteRequest,
    db: Session = Depends(get_db)
):
    """Delete multiple watchlist items."""
    service = WatchlistService(db)
    count = service.delete_batch(request.ids)
    return {"deleted": count}
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_watchlist_batch.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/app/modules/watchlist/
git add backend/tests/test_watchlist_batch.py
git commit -m "feat(watchlist): add batch processing and delete endpoints"
```

---

## Task 2: Watchlist Status Field

**Files:**
- Modify: `backend/src/app/models.py`
- Create: `backend/tests/test_watchlist_status.py`

**Step 1: Write the failing test**

Create `backend/tests/test_watchlist_status.py`:

```python
import pytest
from app.models import Watchlist
from app.database import get_db, Base, engine


def test_watchlist_has_status_field():
    """Watchlist model should have status field."""
    assert hasattr(Watchlist, "status")


def test_watchlist_status_default():
    """Watchlist status should default to 'pending'."""
    item = Watchlist(
        tmdb_id=123,
        media_type="movie",
        title="Test"
    )
    assert item.status == "pending"
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_watchlist_status.py -v`
Expected: FAIL if status field doesn't exist

**Step 3: Write minimal implementation**

Modify `backend/src/app/models.py` - add status to Watchlist:

```python
class Watchlist(Base):
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, index=True)
    tmdb_id = Column(Integer, unique=True, nullable=False)
    media_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    poster_path = Column(String)
    added_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(String)
    status = Column(String, default="pending")  # pending, added, downloading
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_watchlist_status.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/app/models.py
git add backend/tests/test_watchlist_status.py
git commit -m "feat(watchlist): add status field to watchlist model"
```

---

## Task 3: Update Watchlist GET to Include Status

**Files:**
- Modify: `backend/src/app/modules/watchlist/router.py`
- Modify: `backend/tests/test_watchlist_router.py`

**Step 1: Update existing tests**

Add to `backend/tests/test_watchlist_router.py`:

```python
def test_get_watchlist_includes_status():
    """GET /api/watchlist should include status field."""
    # Add item
    client.post("/api/watchlist", json={
        "tmdb_id": 999,
        "media_type": "movie",
        "title": "Status Test"
    })

    response = client.get("/api/watchlist")
    assert response.status_code == 200
    items = response.json()
    assert len(items) > 0
    assert "status" in items[0]
    assert items[0]["status"] == "pending"
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_watchlist_router.py::test_get_watchlist_includes_status -v`
Expected: FAIL if status not returned

**Step 3: Update response schema**

Ensure watchlist response includes status:

```python
# In schemas.py or inline
class WatchlistItemResponse(BaseModel):
    id: int
    tmdb_id: int
    media_type: str
    title: str
    poster_path: Optional[str]
    added_at: datetime
    notes: Optional[str]
    status: str

    class Config:
        from_attributes = True
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_watchlist_router.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/app/modules/watchlist/
git add backend/tests/test_watchlist_router.py
git commit -m "feat(watchlist): include status in watchlist response"
```

---

## Task 4: Frontend Watchlist Service Updates

**Files:**
- Modify: `frontend/src/services/watchlist.js`

**Step 1: Add batch methods**

Add to `frontend/src/services/watchlist.js`:

```javascript
/**
 * Process watchlist items (send to Radarr/Sonarr)
 * @param {number[]} ids - TMDB IDs to process
 * @param {string} mediaType - 'movie' or 'tv'
 */
async processItems(ids, mediaType) {
  const response = await api.post('/watchlist/process', {
    ids,
    media_type: mediaType
  })
  return response
},

/**
 * Delete multiple watchlist items
 * @param {number[]} ids - TMDB IDs to delete
 */
async deleteItems(ids) {
  const response = await api.delete('/watchlist/batch', {
    data: { ids }
  })
  return response
}
```

**Step 2: Commit**

```bash
git add frontend/src/services/watchlist.js
git commit -m "feat(watchlist): add batch methods to frontend service"
```

---

## Task 5: WatchlistView Batch Selection

**Files:**
- Modify: `frontend/src/views/WatchlistView.vue`

**Step 1: Update the view**

Replace `frontend/src/views/WatchlistView.vue`:

```vue
<template>
  <div class="watchlist-view">
    <div class="watchlist-header">
      <h1>Watchlist</h1>

      <!-- Batch Actions -->
      <div v-if="selectedItems.length > 0" class="batch-actions">
        <span class="selection-count">{{ selectedItems.length }} selected</span>
        <button class="btn-process" @click="showProcessModal = true">
          Add to Library
        </button>
        <button class="btn-delete" @click="confirmDelete">
          Remove
        </button>
      </div>
    </div>

    <!-- Filter Tabs -->
    <div class="filter-tabs">
      <button
        :class="['tab', { active: filter === 'all' }]"
        @click="filter = 'all'"
      >
        All ({{ items.length }})
      </button>
      <button
        :class="['tab', { active: filter === 'movies' }]"
        @click="filter = 'movies'"
      >
        Movies ({{ movieCount }})
      </button>
      <button
        :class="['tab', { active: filter === 'shows' }]"
        @click="filter = 'shows'"
      >
        TV Shows ({{ showCount }})
      </button>
    </div>

    <!-- Select All -->
    <div v-if="filteredItems.length > 0" class="select-all">
      <label>
        <input
          type="checkbox"
          :checked="allSelected"
          @change="toggleSelectAll"
        />
        Select All
      </label>
    </div>

    <!-- Watchlist Items -->
    <div v-if="filteredItems.length > 0" class="watchlist-grid">
      <div
        v-for="item in filteredItems"
        :key="item.tmdb_id"
        :class="['watchlist-item', { selected: isSelected(item.tmdb_id) }]"
      >
        <div class="item-checkbox">
          <input
            type="checkbox"
            :checked="isSelected(item.tmdb_id)"
            @change="toggleSelect(item.tmdb_id)"
          />
        </div>

        <router-link
          :to="`/${item.media_type === 'movie' ? 'movie' : 'tv'}/${item.tmdb_id}`"
          class="item-poster"
        >
          <img
            v-if="item.poster_path"
            :src="`https://image.tmdb.org/t/p/w185${item.poster_path}`"
            :alt="item.title"
          />
          <div v-else class="no-poster">?</div>
        </router-link>

        <div class="item-info">
          <router-link
            :to="`/${item.media_type === 'movie' ? 'movie' : 'tv'}/${item.tmdb_id}`"
            class="item-title"
          >
            {{ item.title }}
          </router-link>
          <div class="item-meta">
            <span class="media-type">{{ item.media_type === 'movie' ? 'Movie' : 'TV Show' }}</span>
            <span :class="['status-badge', item.status]">{{ formatStatus(item.status) }}</span>
          </div>
          <div v-if="item.notes" class="item-notes">{{ item.notes }}</div>
          <div class="item-date">Added {{ formatDate(item.added_at) }}</div>
        </div>

        <div class="item-actions">
          <button
            v-if="item.status === 'pending'"
            class="btn-add-single"
            @click="processSingle(item)"
            title="Add to Library"
          >
            ➕
          </button>
          <button
            class="btn-remove-single"
            @click="removeSingle(item.tmdb_id)"
            title="Remove"
          >
            🗑️
          </button>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="empty-state">
      <p>Your watchlist is empty</p>
      <router-link to="/" class="btn-discover">Discover Content</router-link>
    </div>

    <!-- Process Modal -->
    <Teleport to="body">
      <div v-if="showProcessModal" class="modal-overlay" @click="showProcessModal = false">
        <div class="modal-content" @click.stop>
          <h2>Add to Library</h2>
          <p>Add {{ selectedItems.length }} item(s) to your library?</p>

          <div class="modal-summary">
            <div v-if="selectedMovieIds.length">
              <strong>Movies:</strong> {{ selectedMovieIds.length }} → Radarr
            </div>
            <div v-if="selectedShowIds.length">
              <strong>TV Shows:</strong> {{ selectedShowIds.length }} → Sonarr
            </div>
          </div>

          <div class="modal-actions">
            <button class="btn-cancel" @click="showProcessModal = false">Cancel</button>
            <button class="btn-confirm" @click="processSelected" :disabled="processing">
              {{ processing ? 'Processing...' : 'Confirm' }}
            </button>
          </div>

          <div v-if="processResult" class="process-result">
            <div v-if="processResult.processed.length" class="success">
              ✓ {{ processResult.processed.length }} added successfully
            </div>
            <div v-if="processResult.failed.length" class="error">
              ✗ {{ processResult.failed.length }} failed
              <ul>
                <li v-for="fail in processResult.failed" :key="fail.tmdb_id">
                  {{ fail.error }}
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import watchlistService from '@/services/watchlist'

const items = ref([])
const selectedItems = ref([])
const filter = ref('all')
const showProcessModal = ref(false)
const processing = ref(false)
const processResult = ref(null)

onMounted(async () => {
  await loadWatchlist()
})

async function loadWatchlist() {
  try {
    items.value = await watchlistService.getWatchlist()
  } catch (error) {
    console.error('Failed to load watchlist:', error)
  }
}

const filteredItems = computed(() => {
  if (filter.value === 'movies') {
    return items.value.filter(i => i.media_type === 'movie')
  }
  if (filter.value === 'shows') {
    return items.value.filter(i => i.media_type === 'tv')
  }
  return items.value
})

const movieCount = computed(() =>
  items.value.filter(i => i.media_type === 'movie').length
)

const showCount = computed(() =>
  items.value.filter(i => i.media_type === 'tv').length
)

const allSelected = computed(() =>
  filteredItems.value.length > 0 &&
  filteredItems.value.every(i => selectedItems.value.includes(i.tmdb_id))
)

const selectedMovieIds = computed(() =>
  items.value
    .filter(i => selectedItems.value.includes(i.tmdb_id) && i.media_type === 'movie')
    .map(i => i.tmdb_id)
)

const selectedShowIds = computed(() =>
  items.value
    .filter(i => selectedItems.value.includes(i.tmdb_id) && i.media_type === 'tv')
    .map(i => i.tmdb_id)
)

function isSelected(tmdbId) {
  return selectedItems.value.includes(tmdbId)
}

function toggleSelect(tmdbId) {
  const index = selectedItems.value.indexOf(tmdbId)
  if (index === -1) {
    selectedItems.value.push(tmdbId)
  } else {
    selectedItems.value.splice(index, 1)
  }
}

function toggleSelectAll() {
  if (allSelected.value) {
    selectedItems.value = []
  } else {
    selectedItems.value = filteredItems.value.map(i => i.tmdb_id)
  }
}

async function processSelected() {
  processing.value = true
  processResult.value = { processed: [], failed: [] }

  try {
    // Process movies
    if (selectedMovieIds.value.length > 0) {
      const result = await watchlistService.processItems(
        selectedMovieIds.value,
        'movie'
      )
      processResult.value.processed.push(...result.processed)
      processResult.value.failed.push(...result.failed)
    }

    // Process shows
    if (selectedShowIds.value.length > 0) {
      const result = await watchlistService.processItems(
        selectedShowIds.value,
        'tv'
      )
      processResult.value.processed.push(...result.processed)
      processResult.value.failed.push(...result.failed)
    }

    // Refresh list
    await loadWatchlist()
    selectedItems.value = []

  } catch (error) {
    console.error('Process failed:', error)
  } finally {
    processing.value = false
  }
}

async function processSingle(item) {
  try {
    await watchlistService.processItems(
      [item.tmdb_id],
      item.media_type
    )
    await loadWatchlist()
  } catch (error) {
    console.error('Failed to process:', error)
  }
}

async function confirmDelete() {
  if (confirm(`Remove ${selectedItems.value.length} item(s) from watchlist?`)) {
    try {
      await watchlistService.deleteItems(selectedItems.value)
      await loadWatchlist()
      selectedItems.value = []
    } catch (error) {
      console.error('Delete failed:', error)
    }
  }
}

async function removeSingle(tmdbId) {
  try {
    await watchlistService.removeFromWatchlist(tmdbId)
    await loadWatchlist()
  } catch (error) {
    console.error('Failed to remove:', error)
  }
}

function formatStatus(status) {
  const labels = {
    pending: 'Pending',
    added: 'In Library',
    downloading: 'Downloading'
  }
  return labels[status] || status
}

function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString()
}
</script>

<style scoped>
.watchlist-view {
  max-width: 1000px;
  margin: 0 auto;
  padding: 2rem;
}

.watchlist-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.watchlist-header h1 {
  color: #fff;
  margin: 0;
}

.batch-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.selection-count {
  color: #999;
}

.btn-process {
  padding: 0.5rem 1rem;
  background: #e94560;
  border: none;
  border-radius: 4px;
  color: #fff;
  cursor: pointer;
}

.btn-delete {
  padding: 0.5rem 1rem;
  background: transparent;
  border: 1px solid #666;
  border-radius: 4px;
  color: #ccc;
  cursor: pointer;
}

.filter-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.tab {
  padding: 0.5rem 1rem;
  background: transparent;
  border: 1px solid #333;
  border-radius: 4px;
  color: #ccc;
  cursor: pointer;
}

.tab.active {
  background: #252540;
  border-color: #e94560;
  color: #fff;
}

.select-all {
  margin-bottom: 1rem;
  color: #ccc;
}

.select-all input {
  margin-right: 0.5rem;
}

.watchlist-grid {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.watchlist-item {
  display: flex;
  gap: 1rem;
  padding: 1rem;
  background: #1a1a2e;
  border-radius: 8px;
  border: 2px solid transparent;
}

.watchlist-item.selected {
  border-color: #e94560;
}

.item-checkbox {
  display: flex;
  align-items: center;
}

.item-checkbox input {
  width: 20px;
  height: 20px;
  cursor: pointer;
}

.item-poster {
  flex: 0 0 auto;
}

.item-poster img {
  width: 80px;
  border-radius: 4px;
}

.no-poster {
  width: 80px;
  height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #252540;
  border-radius: 4px;
  color: #666;
}

.item-info {
  flex: 1;
}

.item-title {
  color: #fff;
  text-decoration: none;
  font-size: 1.1rem;
}

.item-title:hover {
  color: #e94560;
}

.item-meta {
  display: flex;
  gap: 0.5rem;
  margin: 0.5rem 0;
}

.media-type {
  font-size: 0.85rem;
  color: #999;
}

.status-badge {
  font-size: 0.75rem;
  padding: 0.15rem 0.5rem;
  border-radius: 10px;
}

.status-badge.pending {
  background: #333;
  color: #ccc;
}

.status-badge.added {
  background: rgba(0, 200, 83, 0.2);
  color: #00c853;
}

.status-badge.downloading {
  background: rgba(33, 150, 243, 0.2);
  color: #2196f3;
}

.item-notes {
  font-size: 0.9rem;
  color: #999;
  font-style: italic;
}

.item-date {
  font-size: 0.8rem;
  color: #666;
  margin-top: 0.5rem;
}

.item-actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.btn-add-single, .btn-remove-single {
  padding: 0.5rem;
  background: transparent;
  border: 1px solid #333;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
}

.btn-add-single:hover {
  border-color: #00c853;
}

.btn-remove-single:hover {
  border-color: #e94560;
}

.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  color: #666;
}

.btn-discover {
  display: inline-block;
  margin-top: 1rem;
  padding: 0.75rem 1.5rem;
  background: #e94560;
  border-radius: 4px;
  color: #fff;
  text-decoration: none;
}

/* Modal Styles */
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

.modal-content {
  background: #1a1a2e;
  padding: 2rem;
  border-radius: 8px;
  max-width: 400px;
  width: 90%;
}

.modal-content h2 {
  color: #fff;
  margin: 0 0 1rem;
}

.modal-content p {
  color: #ccc;
  margin-bottom: 1rem;
}

.modal-summary {
  background: #252540;
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 1.5rem;
  color: #ccc;
}

.modal-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
}

.btn-cancel {
  padding: 0.75rem 1.5rem;
  background: transparent;
  border: 1px solid #666;
  border-radius: 4px;
  color: #ccc;
  cursor: pointer;
}

.btn-confirm {
  padding: 0.75rem 1.5rem;
  background: #e94560;
  border: none;
  border-radius: 4px;
  color: #fff;
  cursor: pointer;
}

.btn-confirm:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.process-result {
  margin-top: 1rem;
  padding: 1rem;
  border-radius: 4px;
}

.process-result .success {
  color: #00c853;
}

.process-result .error {
  color: #e94560;
}

.process-result ul {
  margin: 0.5rem 0 0 1rem;
  padding: 0;
  font-size: 0.85rem;
}
</style>
```

**Step 2: Commit**

```bash
git add frontend/src/views/WatchlistView.vue
git commit -m "feat(watchlist): add batch selection and processing UI"
```

---

## Task 6: Update Discovery Page Add Button

**Files:**
- Modify: `frontend/src/components/MediaCard.vue`

**Step 1: Change Add button behavior**

Update MediaCard.vue to add to watchlist instead of directly to Radarr/Sonarr:

```vue
<template>
  <!-- ... existing template ... -->
  <button
    class="btn-add"
    @click.prevent="addToWatchlist"
    :disabled="adding"
    :title="inWatchlist ? 'In Watchlist' : 'Add to Watchlist'"
  >
    {{ adding ? '...' : (inWatchlist ? '✓' : '+') }}
  </button>
</template>

<script setup>
import { ref } from 'vue'
import watchlistService from '@/services/watchlist'

const props = defineProps({
  media: Object,
  mediaType: String
})

const adding = ref(false)
const inWatchlist = ref(false)

async function addToWatchlist() {
  if (inWatchlist.value) return

  adding.value = true
  try {
    await watchlistService.addToWatchlist({
      tmdb_id: props.media.id,
      media_type: props.mediaType === 'movie' ? 'movie' : 'tv',
      title: props.media.title || props.media.name,
      poster_path: props.media.poster_path
    })
    inWatchlist.value = true
  } catch (error) {
    console.error('Failed to add to watchlist:', error)
  } finally {
    adding.value = false
  }
}
</script>
```

**Step 2: Commit**

```bash
git add frontend/src/components/MediaCard.vue
git commit -m "feat(watchlist): change Add button to add to watchlist instead of Radarr/Sonarr"
```

---

## Task 7: Final Testing

**Step 1: Run backend tests**

```bash
cd backend && pytest -v
```

**Step 2: Manual testing**

1. Start servers
2. On discovery page, click "+" on a movie → should add to watchlist
3. Go to Watchlist page
4. Select multiple items with checkboxes
5. Click "Add to Library" → modal appears
6. Confirm → items sent to Radarr/Sonarr
7. Status should update to "In Library"

**Step 3: Final commit**

```bash
git add -A
git commit -m "feat(watchlist): complete watchlist workflow overhaul"
```

---

## Summary

| Task | Description |
|------|-------------|
| 1 | Batch processing endpoint |
| 2 | Watchlist status field |
| 3 | Status in GET response |
| 4 | Frontend service updates |
| 5 | WatchlistView batch UI |
| 6 | MediaCard add to watchlist |
| 7 | Testing |
