# Library Monitor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add visibility into recently added items and current download queue from Radarr/Sonarr.

**Architecture:** New endpoints for Radarr/Sonarr history and queue APIs. New LibraryView page with tabs for recent activity and downloads. Auto-refresh capability.

**Tech Stack:** FastAPI, Radarr/Sonarr APIs, Vue 3, polling

---

## Task 1: Radarr Queue Endpoint

**Files:**
- Modify: `backend/src/app/modules/radarr/client.py`
- Modify: `backend/src/app/modules/radarr/router.py`
- Create: `backend/tests/test_radarr_queue.py`

**Step 1: Write the failing test**

Create `backend/tests/test_radarr_queue.py`:

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app


client = TestClient(app)


def test_get_radarr_queue():
    """GET /api/radarr/queue should return download queue."""
    with patch('app.modules.radarr.client.RadarrClient.get_queue') as mock:
        mock.return_value = {
            "records": [
                {
                    "id": 1,
                    "movieId": 123,
                    "title": "Test Movie",
                    "status": "downloading",
                    "sizeleft": 1000000000,
                    "size": 2000000000,
                    "timeleft": "01:30:00"
                }
            ],
            "totalRecords": 1
        }

        response = client.get("/api/radarr/queue")
        assert response.status_code == 200
        data = response.json()
        assert "records" in data
        assert len(data["records"]) == 1


def test_get_radarr_queue_empty():
    """GET /api/radarr/queue should handle empty queue."""
    with patch('app.modules.radarr.client.RadarrClient.get_queue') as mock:
        mock.return_value = {"records": [], "totalRecords": 0}

        response = client.get("/api/radarr/queue")
        assert response.status_code == 200
        data = response.json()
        assert data["records"] == []
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_radarr_queue.py -v`
Expected: FAIL with 404

**Step 3: Write minimal implementation**

Add to `backend/src/app/modules/radarr/client.py`:

```python
async def get_queue(self) -> dict:
    """Get current download queue from Radarr."""
    url = f"{self.base_url}/api/v3/queue"
    params = {
        "page": 1,
        "pageSize": 50,
        "includeMovie": True
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            params=params,
            headers={"X-Api-Key": self.api_key}
        )
        response.raise_for_status()
        return response.json()
```

Add to `backend/src/app/modules/radarr/router.py`:

```python
@router.get("/queue")
async def get_radarr_queue():
    """Get current download queue from Radarr."""
    client = RadarrClient()
    return await client.get_queue()
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_radarr_queue.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/app/modules/radarr/
git add backend/tests/test_radarr_queue.py
git commit -m "feat(library): add Radarr queue endpoint"
```

---

## Task 2: Radarr Recent Endpoint

**Files:**
- Modify: `backend/src/app/modules/radarr/client.py`
- Modify: `backend/src/app/modules/radarr/router.py`
- Create: `backend/tests/test_radarr_recent.py`

**Step 1: Write the failing test**

Create `backend/tests/test_radarr_recent.py`:

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app


client = TestClient(app)


def test_get_radarr_recent():
    """GET /api/radarr/recent should return recently added movies."""
    with patch('app.modules.radarr.client.RadarrClient.get_recent') as mock:
        mock.return_value = [
            {
                "id": 1,
                "title": "Recently Added Movie",
                "tmdbId": 12345,
                "added": "2026-01-28T10:00:00Z",
                "hasFile": True
            }
        ]

        response = client.get("/api/radarr/recent")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["title"] == "Recently Added Movie"
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_radarr_recent.py -v`
Expected: FAIL with 404

**Step 3: Write minimal implementation**

Add to `backend/src/app/modules/radarr/client.py`:

```python
async def get_recent(self, limit: int = 20) -> list:
    """Get recently added movies from Radarr."""
    url = f"{self.base_url}/api/v3/movie"
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers={"X-Api-Key": self.api_key}
        )
        response.raise_for_status()
        movies = response.json()

        # Sort by added date, most recent first
        movies.sort(key=lambda m: m.get("added", ""), reverse=True)

        # Return only movies with files (completed downloads)
        return [m for m in movies if m.get("hasFile")][:limit]
```

Add to `backend/src/app/modules/radarr/router.py`:

```python
from fastapi import Query

@router.get("/recent")
async def get_radarr_recent(limit: int = Query(20, le=100)):
    """Get recently added movies from Radarr."""
    client = RadarrClient()
    return await client.get_recent(limit)
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_radarr_recent.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/app/modules/radarr/
git add backend/tests/test_radarr_recent.py
git commit -m "feat(library): add Radarr recent additions endpoint"
```

---

## Task 3: Sonarr Queue Endpoint

**Files:**
- Modify: `backend/src/app/modules/sonarr/client.py`
- Modify: `backend/src/app/modules/sonarr/router.py`
- Create: `backend/tests/test_sonarr_queue.py`

**Step 1: Write the failing test**

Create `backend/tests/test_sonarr_queue.py`:

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app


client = TestClient(app)


def test_get_sonarr_queue():
    """GET /api/sonarr/queue should return download queue."""
    with patch('app.modules.sonarr.client.SonarrClient.get_queue') as mock:
        mock.return_value = {
            "records": [
                {
                    "id": 1,
                    "seriesId": 456,
                    "title": "Test Show S01E01",
                    "status": "downloading",
                    "sizeleft": 500000000,
                    "size": 1000000000,
                    "timeleft": "00:45:00"
                }
            ],
            "totalRecords": 1
        }

        response = client.get("/api/sonarr/queue")
        assert response.status_code == 200
        data = response.json()
        assert "records" in data
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_sonarr_queue.py -v`
Expected: FAIL with 404

**Step 3: Write minimal implementation**

Add to `backend/src/app/modules/sonarr/client.py`:

```python
async def get_queue(self) -> dict:
    """Get current download queue from Sonarr."""
    url = f"{self.base_url}/api/v3/queue"
    params = {
        "page": 1,
        "pageSize": 50,
        "includeSeries": True,
        "includeEpisode": True
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            params=params,
            headers={"X-Api-Key": self.api_key}
        )
        response.raise_for_status()
        return response.json()
```

Add to `backend/src/app/modules/sonarr/router.py`:

```python
@router.get("/queue")
async def get_sonarr_queue():
    """Get current download queue from Sonarr."""
    client = SonarrClient()
    return await client.get_queue()
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_sonarr_queue.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/app/modules/sonarr/
git add backend/tests/test_sonarr_queue.py
git commit -m "feat(library): add Sonarr queue endpoint"
```

---

## Task 4: Sonarr Recent Endpoint

**Files:**
- Modify: `backend/src/app/modules/sonarr/client.py`
- Modify: `backend/src/app/modules/sonarr/router.py`
- Create: `backend/tests/test_sonarr_recent.py`

**Step 1: Write the failing test**

Create `backend/tests/test_sonarr_recent.py`:

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app


client = TestClient(app)


def test_get_sonarr_recent():
    """GET /api/sonarr/recent should return recently added shows."""
    with patch('app.modules.sonarr.client.SonarrClient.get_recent') as mock:
        mock.return_value = [
            {
                "id": 1,
                "title": "Recently Added Show",
                "tvdbId": 67890,
                "added": "2026-01-28T10:00:00Z"
            }
        ]

        response = client.get("/api/sonarr/recent")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_sonarr_recent.py -v`
Expected: FAIL with 404

**Step 3: Write minimal implementation**

Add to `backend/src/app/modules/sonarr/client.py`:

```python
async def get_recent(self, limit: int = 20) -> list:
    """Get recently added shows from Sonarr."""
    url = f"{self.base_url}/api/v3/series"
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers={"X-Api-Key": self.api_key}
        )
        response.raise_for_status()
        shows = response.json()

        # Sort by added date, most recent first
        shows.sort(key=lambda s: s.get("added", ""), reverse=True)

        return shows[:limit]
```

Add to `backend/src/app/modules/sonarr/router.py`:

```python
from fastapi import Query

@router.get("/recent")
async def get_sonarr_recent(limit: int = Query(20, le=100)):
    """Get recently added shows from Sonarr."""
    client = SonarrClient()
    return await client.get_recent(limit)
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_sonarr_recent.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/app/modules/sonarr/
git add backend/tests/test_sonarr_recent.py
git commit -m "feat(library): add Sonarr recent additions endpoint"
```

---

## Task 5: Combined Activity Endpoint

**Files:**
- Create: `backend/src/app/modules/library/__init__.py`
- Create: `backend/src/app/modules/library/router.py`
- Create: `backend/tests/test_library_activity.py`
- Modify: `backend/src/app/main.py`

**Step 1: Write the failing test**

Create `backend/tests/test_library_activity.py`:

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app


client = TestClient(app)


def test_get_library_activity():
    """GET /api/library/activity should return combined activity."""
    with patch('app.modules.radarr.client.RadarrClient.get_recent') as mock_radarr:
        with patch('app.modules.sonarr.client.SonarrClient.get_recent') as mock_sonarr:
            mock_radarr.return_value = [
                {"id": 1, "title": "Movie", "added": "2026-01-28T10:00:00Z", "tmdbId": 123}
            ]
            mock_sonarr.return_value = [
                {"id": 2, "title": "Show", "added": "2026-01-28T11:00:00Z", "tvdbId": 456}
            ]

            response = client.get("/api/library/activity")
            assert response.status_code == 200
            data = response.json()
            assert "movies" in data
            assert "shows" in data
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_library_activity.py -v`
Expected: FAIL with 404

**Step 3: Write minimal implementation**

Create `backend/src/app/modules/library/__init__.py`:

```python
# Library module
```

Create `backend/src/app/modules/library/router.py`:

```python
from fastapi import APIRouter, Query
from app.modules.radarr.client import RadarrClient
from app.modules.sonarr.client import SonarrClient

router = APIRouter(prefix="/api/library", tags=["library"])


@router.get("/activity")
async def get_library_activity(limit: int = Query(20, le=100)):
    """Get combined recent activity from Radarr and Sonarr."""
    radarr = RadarrClient()
    sonarr = SonarrClient()

    movies = await radarr.get_recent(limit)
    shows = await sonarr.get_recent(limit)

    return {
        "movies": movies,
        "shows": shows
    }


@router.get("/queue")
async def get_combined_queue():
    """Get combined download queue from Radarr and Sonarr."""
    radarr = RadarrClient()
    sonarr = SonarrClient()

    radarr_queue = await radarr.get_queue()
    sonarr_queue = await sonarr.get_queue()

    return {
        "movies": radarr_queue.get("records", []),
        "shows": sonarr_queue.get("records", [])
    }
```

Add to `backend/src/app/main.py`:

```python
from app.modules.library.router import router as library_router

app.include_router(library_router)
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_library_activity.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/app/modules/library/
git add backend/tests/test_library_activity.py
git add backend/src/app/main.py
git commit -m "feat(library): add combined activity and queue endpoints"
```

---

## Task 6: Frontend Library Service

**Files:**
- Create: `frontend/src/services/library.js`

**Step 1: Create the service**

Create `frontend/src/services/library.js`:

```javascript
import api from './api'

export default {
  /**
   * Get recent activity (movies and shows added)
   */
  async getActivity(limit = 20) {
    const response = await api.get(`/library/activity?limit=${limit}`)
    return response
  },

  /**
   * Get combined download queue
   */
  async getQueue() {
    const response = await api.get('/library/queue')
    return response
  },

  /**
   * Get Radarr queue only
   */
  async getRadarrQueue() {
    const response = await api.get('/radarr/queue')
    return response
  },

  /**
   * Get Sonarr queue only
   */
  async getSonarrQueue() {
    const response = await api.get('/sonarr/queue')
    return response
  },

  /**
   * Get recently added movies
   */
  async getRecentMovies(limit = 20) {
    const response = await api.get(`/radarr/recent?limit=${limit}`)
    return response
  },

  /**
   * Get recently added shows
   */
  async getRecentShows(limit = 20) {
    const response = await api.get(`/sonarr/recent?limit=${limit}`)
    return response
  }
}
```

**Step 2: Commit**

```bash
git add frontend/src/services/library.js
git commit -m "feat(library): add frontend library service"
```

---

## Task 7: DownloadProgress Component

**Files:**
- Create: `frontend/src/components/DownloadProgress.vue`

**Step 1: Create the component**

Create `frontend/src/components/DownloadProgress.vue`:

```vue
<template>
  <div class="download-progress">
    <div class="progress-bar">
      <div
        class="progress-fill"
        :style="{ width: `${percentage}%` }"
      ></div>
    </div>
    <div class="progress-info">
      <span class="percentage">{{ percentage }}%</span>
      <span v-if="timeLeft" class="time-left">{{ timeLeft }} remaining</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  size: {
    type: Number,
    default: 0
  },
  sizeLeft: {
    type: Number,
    default: 0
  },
  timeleft: {
    type: String,
    default: ''
  }
})

const percentage = computed(() => {
  if (!props.size || props.size === 0) return 0
  const downloaded = props.size - props.sizeLeft
  return Math.round((downloaded / props.size) * 100)
})

const timeLeft = computed(() => {
  if (!props.timeleft) return null

  // Parse time format (HH:MM:SS or similar)
  const parts = props.timeleft.split(':')
  if (parts.length === 3) {
    const hours = parseInt(parts[0])
    const minutes = parseInt(parts[1])

    if (hours > 0) {
      return `${hours}h ${minutes}m`
    }
    return `${minutes}m`
  }
  return props.timeleft
})
</script>

<style scoped>
.download-progress {
  width: 100%;
}

.progress-bar {
  height: 6px;
  background: #252540;
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #e94560, #ff6b6b);
  border-radius: 3px;
  transition: width 0.3s ease;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  margin-top: 0.25rem;
  font-size: 0.75rem;
  color: #999;
}

.percentage {
  color: #e94560;
}
</style>
```

**Step 2: Commit**

```bash
git add frontend/src/components/DownloadProgress.vue
git commit -m "feat(library): add DownloadProgress component"
```

---

## Task 8: QueueItem Component

**Files:**
- Create: `frontend/src/components/QueueItem.vue`

**Step 1: Create the component**

Create `frontend/src/components/QueueItem.vue`:

```vue
<template>
  <div class="queue-item">
    <div class="item-poster">
      <img
        v-if="posterPath"
        :src="posterPath"
        :alt="title"
      />
      <div v-else class="no-poster">?</div>
    </div>

    <div class="item-info">
      <div class="item-title">{{ title }}</div>
      <div class="item-subtitle">{{ subtitle }}</div>
      <div class="item-status">
        <span :class="['status-badge', statusClass]">{{ status }}</span>
      </div>
      <DownloadProgress
        v-if="isDownloading"
        :size="item.size"
        :size-left="item.sizeleft"
        :timeleft="item.timeleft"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import DownloadProgress from './DownloadProgress.vue'

const props = defineProps({
  item: {
    type: Object,
    required: true
  },
  type: {
    type: String,
    default: 'movie'
  }
})

const title = computed(() => {
  if (props.type === 'movie') {
    return props.item.movie?.title || props.item.title || 'Unknown'
  }
  return props.item.series?.title || props.item.title || 'Unknown'
})

const subtitle = computed(() => {
  if (props.type === 'show' && props.item.episode) {
    const ep = props.item.episode
    return `S${String(ep.seasonNumber).padStart(2, '0')}E${String(ep.episodeNumber).padStart(2, '0')} - ${ep.title}`
  }
  return props.item.quality?.quality?.name || ''
})

const posterPath = computed(() => {
  if (props.type === 'movie' && props.item.movie?.images) {
    const poster = props.item.movie.images.find(i => i.coverType === 'poster')
    return poster?.remoteUrl || null
  }
  if (props.type === 'show' && props.item.series?.images) {
    const poster = props.item.series.images.find(i => i.coverType === 'poster')
    return poster?.remoteUrl || null
  }
  return null
})

const status = computed(() => {
  const s = props.item.status?.toLowerCase() || ''
  if (s.includes('download')) return 'Downloading'
  if (s.includes('import')) return 'Importing'
  if (s.includes('queue')) return 'Queued'
  if (s.includes('pause')) return 'Paused'
  return props.item.status || 'Unknown'
})

const statusClass = computed(() => {
  const s = status.value.toLowerCase()
  if (s.includes('download')) return 'downloading'
  if (s.includes('import')) return 'importing'
  if (s.includes('queue')) return 'queued'
  if (s.includes('pause')) return 'paused'
  return ''
})

const isDownloading = computed(() => {
  return status.value.toLowerCase().includes('download')
})
</script>

<style scoped>
.queue-item {
  display: flex;
  gap: 1rem;
  padding: 1rem;
  background: #1a1a2e;
  border-radius: 8px;
}

.item-poster {
  flex: 0 0 auto;
}

.item-poster img {
  width: 60px;
  height: 90px;
  object-fit: cover;
  border-radius: 4px;
}

.no-poster {
  width: 60px;
  height: 90px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #252540;
  border-radius: 4px;
  color: #666;
}

.item-info {
  flex: 1;
  min-width: 0;
}

.item-title {
  color: #fff;
  font-size: 1rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-subtitle {
  color: #999;
  font-size: 0.85rem;
  margin: 0.25rem 0;
}

.item-status {
  margin: 0.5rem 0;
}

.status-badge {
  font-size: 0.75rem;
  padding: 0.2rem 0.5rem;
  border-radius: 10px;
  background: #333;
  color: #ccc;
}

.status-badge.downloading {
  background: rgba(233, 69, 96, 0.2);
  color: #e94560;
}

.status-badge.importing {
  background: rgba(33, 150, 243, 0.2);
  color: #2196f3;
}

.status-badge.queued {
  background: rgba(255, 193, 7, 0.2);
  color: #ffc107;
}

.status-badge.paused {
  background: rgba(158, 158, 158, 0.2);
  color: #9e9e9e;
}
</style>
```

**Step 2: Commit**

```bash
git add frontend/src/components/QueueItem.vue
git commit -m "feat(library): add QueueItem component"
```

---

## Task 9: LibraryView Page

**Files:**
- Create: `frontend/src/views/LibraryView.vue`
- Modify: `frontend/src/router/index.js`

**Step 1: Create the view**

Create `frontend/src/views/LibraryView.vue`:

```vue
<template>
  <div class="library-view">
    <div class="library-header">
      <h1>Library</h1>
      <div class="auto-refresh">
        <label>
          <input type="checkbox" v-model="autoRefresh" />
          Auto-refresh (30s)
        </label>
      </div>
    </div>

    <!-- Tabs -->
    <div class="tabs">
      <button
        :class="['tab', { active: activeTab === 'recent' }]"
        @click="activeTab = 'recent'"
      >
        Recently Added
      </button>
      <button
        :class="['tab', { active: activeTab === 'downloads' }]"
        @click="activeTab = 'downloads'"
      >
        Downloads
        <span v-if="totalDownloads > 0" class="badge">{{ totalDownloads }}</span>
      </button>
    </div>

    <!-- Recently Added Tab -->
    <div v-if="activeTab === 'recent'" class="tab-content">
      <div class="media-type-tabs">
        <button
          :class="['sub-tab', { active: recentType === 'movies' }]"
          @click="recentType = 'movies'"
        >
          Movies ({{ activity.movies?.length || 0 }})
        </button>
        <button
          :class="['sub-tab', { active: recentType === 'shows' }]"
          @click="recentType = 'shows'"
        >
          TV Shows ({{ activity.shows?.length || 0 }})
        </button>
      </div>

      <div v-if="loading" class="loading">Loading...</div>

      <div v-else-if="recentItems.length" class="recent-grid">
        <div
          v-for="item in recentItems"
          :key="item.id"
          class="recent-item"
        >
          <div class="item-poster">
            <img
              v-if="getItemPoster(item)"
              :src="getItemPoster(item)"
              :alt="item.title"
            />
            <div v-else class="no-poster">?</div>
          </div>
          <div class="item-info">
            <div class="item-title">{{ item.title }}</div>
            <div class="item-date">{{ formatDate(item.added) }}</div>
          </div>
        </div>
      </div>

      <div v-else class="empty">
        No recent {{ recentType === 'movies' ? 'movies' : 'shows' }}
      </div>
    </div>

    <!-- Downloads Tab -->
    <div v-if="activeTab === 'downloads'" class="tab-content">
      <div class="media-type-tabs">
        <button
          :class="['sub-tab', { active: queueType === 'movies' }]"
          @click="queueType = 'movies'"
        >
          Movies ({{ queue.movies?.length || 0 }})
        </button>
        <button
          :class="['sub-tab', { active: queueType === 'shows' }]"
          @click="queueType = 'shows'"
        >
          TV Shows ({{ queue.shows?.length || 0 }})
        </button>
      </div>

      <div v-if="loading" class="loading">Loading...</div>

      <div v-else-if="queueItems.length" class="queue-list">
        <QueueItem
          v-for="item in queueItems"
          :key="item.id"
          :item="item"
          :type="queueType === 'movies' ? 'movie' : 'show'"
        />
      </div>

      <div v-else class="empty">
        No downloads in queue
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import libraryService from '@/services/library'
import QueueItem from '@/components/QueueItem.vue'

const activeTab = ref('recent')
const recentType = ref('movies')
const queueType = ref('movies')
const loading = ref(true)
const autoRefresh = ref(false)

const activity = ref({ movies: [], shows: [] })
const queue = ref({ movies: [], shows: [] })

let refreshInterval = null

onMounted(async () => {
  await loadData()
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})

watch(autoRefresh, (enabled) => {
  if (enabled) {
    refreshInterval = setInterval(loadData, 30000)
  } else if (refreshInterval) {
    clearInterval(refreshInterval)
    refreshInterval = null
  }
})

async function loadData() {
  loading.value = true
  try {
    const [activityData, queueData] = await Promise.all([
      libraryService.getActivity(),
      libraryService.getQueue()
    ])
    activity.value = activityData
    queue.value = queueData
  } catch (error) {
    console.error('Failed to load library data:', error)
  } finally {
    loading.value = false
  }
}

const recentItems = computed(() => {
  if (recentType.value === 'movies') {
    return activity.value.movies || []
  }
  return activity.value.shows || []
})

const queueItems = computed(() => {
  if (queueType.value === 'movies') {
    return queue.value.movies || []
  }
  return queue.value.shows || []
})

const totalDownloads = computed(() => {
  return (queue.value.movies?.length || 0) + (queue.value.shows?.length || 0)
})

function getItemPoster(item) {
  // Radarr movie
  if (item.images) {
    const poster = item.images.find(i => i.coverType === 'poster')
    return poster?.remoteUrl || null
  }
  return null
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  })
}
</script>

<style scoped>
.library-view {
  max-width: 1000px;
  margin: 0 auto;
  padding: 2rem;
}

.library-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.library-header h1 {
  color: #fff;
  margin: 0;
}

.auto-refresh {
  color: #999;
  font-size: 0.9rem;
}

.auto-refresh input {
  margin-right: 0.5rem;
}

.tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}

.tab {
  padding: 0.75rem 1.5rem;
  background: transparent;
  border: 1px solid #333;
  border-radius: 4px;
  color: #ccc;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.tab.active {
  background: #e94560;
  border-color: #e94560;
  color: #fff;
}

.badge {
  background: #fff;
  color: #e94560;
  font-size: 0.75rem;
  padding: 0.1rem 0.4rem;
  border-radius: 10px;
}

.media-type-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.sub-tab {
  padding: 0.5rem 1rem;
  background: transparent;
  border: 1px solid #333;
  border-radius: 4px;
  color: #999;
  cursor: pointer;
  font-size: 0.9rem;
}

.sub-tab.active {
  background: #252540;
  border-color: #666;
  color: #fff;
}

.recent-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 1.5rem;
}

.recent-item {
  text-decoration: none;
  color: inherit;
}

.item-poster img {
  width: 100%;
  aspect-ratio: 2/3;
  object-fit: cover;
  border-radius: 8px;
}

.no-poster {
  width: 100%;
  aspect-ratio: 2/3;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #252540;
  border-radius: 8px;
  color: #666;
  font-size: 2rem;
}

.item-info {
  padding: 0.5rem 0;
}

.item-title {
  color: #fff;
  font-size: 0.9rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-date {
  color: #666;
  font-size: 0.8rem;
}

.queue-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.loading {
  text-align: center;
  padding: 2rem;
  color: #666;
}

.empty {
  text-align: center;
  padding: 3rem;
  color: #666;
  background: #1a1a2e;
  border-radius: 8px;
}
</style>
```

**Step 2: Add route**

Add to `frontend/src/router/index.js`:

```javascript
// Add import
import LibraryView from '@/views/LibraryView.vue'

// Add route
{
  path: '/library',
  name: 'Library',
  component: LibraryView
}
```

**Step 3: Commit**

```bash
git add frontend/src/views/LibraryView.vue
git add frontend/src/router/index.js
git commit -m "feat(library): add LibraryView with recent and downloads tabs"
```

---

## Task 10: Update Navigation

**Files:**
- Modify: `frontend/src/App.vue`

**Step 1: Add library link to navigation**

Add library link to navigation:

```vue
<router-link to="/library" class="nav-link">Library</router-link>
```

**Step 2: Commit**

```bash
git add frontend/src/App.vue
git commit -m "feat(library): add library link to navigation"
```

---

## Task 11: Final Testing

**Step 1: Run backend tests**

```bash
cd backend && pytest -v
```

**Step 2: Manual testing**

1. Start servers
2. Navigate to Library page
3. Check "Recently Added" tab - shows movies/shows from Radarr/Sonarr
4. Check "Downloads" tab - shows current queue
5. Toggle auto-refresh - should update every 30s
6. Verify progress bars show correctly

**Step 3: Final commit**

```bash
git add -A
git commit -m "feat(library): complete library monitor feature"
```

---

## Summary

| Task | Description |
|------|-------------|
| 1 | Radarr queue endpoint |
| 2 | Radarr recent endpoint |
| 3 | Sonarr queue endpoint |
| 4 | Sonarr recent endpoint |
| 5 | Combined activity endpoint |
| 6 | Frontend library service |
| 7 | DownloadProgress component |
| 8 | QueueItem component |
| 9 | LibraryView page |
| 10 | Navigation update |
| 11 | Testing |
