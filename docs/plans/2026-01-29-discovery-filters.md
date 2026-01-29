# Discovery Filters Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add genre, year, rating, and content rating filters to the discovery page.

**Architecture:** Extend existing discovery endpoints with query parameters. Add genre list endpoints. Frontend filter panel with reactive updates.

**Tech Stack:** FastAPI, TMDB API, Vue 3, Composition API

---

## Task 1: Genre Endpoints

**Files:**
- Modify: `backend/src/app/modules/discovery/router.py`
- Modify: `backend/src/app/modules/discovery/client.py`
- Create: `backend/tests/test_genre_endpoints.py`

**Step 1: Write the failing test**

Create `backend/tests/test_genre_endpoints.py`:

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_get_movie_genres():
    """GET /api/genres/movies should return genre list."""
    response = client.get("/api/genres/movies")
    assert response.status_code == 200
    data = response.json()
    assert "genres" in data
    assert isinstance(data["genres"], list)
    if len(data["genres"]) > 0:
        assert "id" in data["genres"][0]
        assert "name" in data["genres"][0]


def test_get_tv_genres():
    """GET /api/genres/shows should return genre list."""
    response = client.get("/api/genres/shows")
    assert response.status_code == 200
    data = response.json()
    assert "genres" in data
    assert isinstance(data["genres"], list)
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_genre_endpoints.py -v`
Expected: FAIL with 404 (route not found)

**Step 3: Write minimal implementation**

Add to `backend/src/app/modules/discovery/client.py`:

```python
async def get_movie_genres(self) -> dict:
    """Get list of movie genres from TMDB."""
    url = f"{self.base_url}/genre/movie/list"
    params = {"api_key": self.api_key}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()


async def get_tv_genres(self) -> dict:
    """Get list of TV genres from TMDB."""
    url = f"{self.base_url}/genre/tv/list"
    params = {"api_key": self.api_key}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()
```

Add to `backend/src/app/modules/discovery/router.py`:

```python
@router.get("/genres/movies")
async def get_movie_genres():
    """Get list of movie genres."""
    client = TMDBClient()
    return await client.get_movie_genres()


@router.get("/genres/shows")
async def get_tv_genres():
    """Get list of TV show genres."""
    client = TMDBClient()
    return await client.get_tv_genres()
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_genre_endpoints.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/app/modules/discovery/client.py
git add backend/src/app/modules/discovery/router.py
git add backend/tests/test_genre_endpoints.py
git commit -m "feat(discovery): add genre list endpoints"
```

---

## Task 2: Filter Parameters Schema

**Files:**
- Create: `backend/src/app/modules/discovery/schemas.py`
- Create: `backend/tests/test_discovery_schemas.py`

**Step 1: Write the failing test**

Create `backend/tests/test_discovery_schemas.py`:

```python
import pytest
from app.modules.discovery.schemas import DiscoveryFilters


def test_filters_default_values():
    """Filters should have sensible defaults."""
    filters = DiscoveryFilters()
    assert filters.genre is None
    assert filters.year is None
    assert filters.rating_gte is None
    assert filters.sort_by == "popularity.desc"


def test_filters_with_values():
    """Filters should accept all parameters."""
    filters = DiscoveryFilters(
        genre="28,12",
        year=2024,
        year_gte=2020,
        year_lte=2025,
        rating_gte=7.0,
        certification="PG-13",
        sort_by="vote_average.desc"
    )
    assert filters.genre == "28,12"
    assert filters.year == 2024
    assert filters.rating_gte == 7.0


def test_filters_to_tmdb_params():
    """Filters should convert to TMDB API params."""
    filters = DiscoveryFilters(
        genre="28",
        year=2024,
        rating_gte=7.0,
        sort_by="popularity.desc"
    )
    params = filters.to_tmdb_params(media_type="movie")
    assert params["with_genres"] == "28"
    assert params["primary_release_year"] == 2024
    assert params["vote_average.gte"] == 7.0
    assert params["sort_by"] == "popularity.desc"
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_discovery_schemas.py -v`
Expected: FAIL with "No module named 'app.modules.discovery.schemas'"

**Step 3: Write minimal implementation**

Create `backend/src/app/modules/discovery/schemas.py`:

```python
from typing import Optional, Literal
from pydantic import BaseModel, Field


class DiscoveryFilters(BaseModel):
    """Query parameters for discovery filtering."""

    genre: Optional[str] = Field(None, description="Comma-separated genre IDs")
    year: Optional[int] = Field(None, description="Exact release year")
    year_gte: Optional[int] = Field(None, description="Released on or after year")
    year_lte: Optional[int] = Field(None, description="Released on or before year")
    rating_gte: Optional[float] = Field(None, ge=0, le=10, description="Minimum rating")
    certification: Optional[str] = Field(None, description="Content rating (PG-13, R, etc)")
    sort_by: str = Field("popularity.desc", description="Sort order")

    def to_tmdb_params(self, media_type: str = "movie") -> dict:
        """Convert filters to TMDB API parameters."""
        params = {}

        if self.genre:
            params["with_genres"] = self.genre

        if self.sort_by:
            params["sort_by"] = self.sort_by

        if self.rating_gte is not None:
            params["vote_average.gte"] = self.rating_gte
            # Require minimum vote count to avoid obscure titles
            params["vote_count.gte"] = 50

        # Year handling differs by media type
        if media_type == "movie":
            if self.year:
                params["primary_release_year"] = self.year
            if self.year_gte:
                params["primary_release_date.gte"] = f"{self.year_gte}-01-01"
            if self.year_lte:
                params["primary_release_date.lte"] = f"{self.year_lte}-12-31"
        else:  # TV
            if self.year:
                params["first_air_date_year"] = self.year
            if self.year_gte:
                params["first_air_date.gte"] = f"{self.year_gte}-01-01"
            if self.year_lte:
                params["first_air_date.lte"] = f"{self.year_lte}-12-31"

        if self.certification:
            params["certification"] = self.certification
            params["certification_country"] = "US"

        return params
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_discovery_schemas.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/app/modules/discovery/schemas.py
git add backend/tests/test_discovery_schemas.py
git commit -m "feat(discovery): add filter parameters schema"
```

---

## Task 3: Filtered Discovery Endpoints

**Files:**
- Modify: `backend/src/app/modules/discovery/client.py`
- Modify: `backend/src/app/modules/discovery/router.py`
- Create: `backend/tests/test_filtered_discovery.py`

**Step 1: Write the failing test**

Create `backend/tests/test_filtered_discovery.py`:

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_discover_movies_with_genre():
    """Discover movies filtered by genre."""
    response = client.get("/api/discover/movies?genre=28")  # Action
    assert response.status_code == 200
    data = response.json()
    assert "results" in data


def test_discover_movies_with_year():
    """Discover movies filtered by year."""
    response = client.get("/api/discover/movies?year=2024")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data


def test_discover_movies_with_rating():
    """Discover movies filtered by minimum rating."""
    response = client.get("/api/discover/movies?rating_gte=7.5")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data


def test_discover_movies_with_sort():
    """Discover movies with custom sort."""
    response = client.get("/api/discover/movies?sort_by=vote_average.desc")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data


def test_discover_shows_with_filters():
    """Discover TV shows with filters."""
    response = client.get("/api/discover/shows?genre=18&year_gte=2020")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_filtered_discovery.py -v`
Expected: FAIL (parameters not recognized or not working)

**Step 3: Write minimal implementation**

Modify `backend/src/app/modules/discovery/client.py` - update discover methods:

```python
async def discover_movies(self, page: int = 1, filters: dict = None) -> dict:
    """Discover movies with optional filters."""
    url = f"{self.base_url}/discover/movie"
    params = {
        "api_key": self.api_key,
        "page": page,
        "include_adult": False,
    }
    if filters:
        params.update(filters)

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()


async def discover_shows(self, page: int = 1, filters: dict = None) -> dict:
    """Discover TV shows with optional filters."""
    url = f"{self.base_url}/discover/tv"
    params = {
        "api_key": self.api_key,
        "page": page,
        "include_adult": False,
    }
    if filters:
        params.update(filters)

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()
```

Modify `backend/src/app/modules/discovery/router.py`:

```python
from fastapi import APIRouter, Query
from typing import Optional
from app.modules.discovery.client import TMDBClient
from app.modules.discovery.schemas import DiscoveryFilters


@router.get("/discover/movies")
async def discover_movies(
    page: int = Query(1, ge=1),
    genre: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    year_gte: Optional[int] = Query(None),
    year_lte: Optional[int] = Query(None),
    rating_gte: Optional[float] = Query(None, ge=0, le=10),
    certification: Optional[str] = Query(None),
    sort_by: str = Query("popularity.desc"),
):
    """Discover movies with filters."""
    client = TMDBClient()
    filters = DiscoveryFilters(
        genre=genre,
        year=year,
        year_gte=year_gte,
        year_lte=year_lte,
        rating_gte=rating_gte,
        certification=certification,
        sort_by=sort_by,
    )
    return await client.discover_movies(page=page, filters=filters.to_tmdb_params("movie"))


@router.get("/discover/shows")
async def discover_shows(
    page: int = Query(1, ge=1),
    genre: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    year_gte: Optional[int] = Query(None),
    year_lte: Optional[int] = Query(None),
    rating_gte: Optional[float] = Query(None, ge=0, le=10),
    sort_by: str = Query("popularity.desc"),
):
    """Discover TV shows with filters."""
    client = TMDBClient()
    filters = DiscoveryFilters(
        genre=genre,
        year=year,
        year_gte=year_gte,
        year_lte=year_lte,
        rating_gte=rating_gte,
        sort_by=sort_by,
    )
    return await client.discover_shows(page=page, filters=filters.to_tmdb_params("tv"))
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_filtered_discovery.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/app/modules/discovery/client.py
git add backend/src/app/modules/discovery/router.py
git add backend/tests/test_filtered_discovery.py
git commit -m "feat(discovery): add filter parameters to discover endpoints"
```

---

## Task 4: Frontend Genre Service

**Files:**
- Modify: `frontend/src/services/discover.js`

**Step 1: Add genre methods to service**

Modify `frontend/src/services/discover.js`:

```javascript
// Add these methods

/**
 * Get list of movie genres
 */
async getMovieGenres() {
  const response = await api.get('/genres/movies')
  return response.genres
},

/**
 * Get list of TV genres
 */
async getTvGenres() {
  const response = await api.get('/genres/shows')
  return response.genres
},

/**
 * Discover movies with filters
 * @param {Object} options - Filter options
 */
async discoverMovies(options = {}) {
  const params = new URLSearchParams()
  if (options.page) params.append('page', options.page)
  if (options.genre) params.append('genre', options.genre)
  if (options.year) params.append('year', options.year)
  if (options.yearGte) params.append('year_gte', options.yearGte)
  if (options.yearLte) params.append('year_lte', options.yearLte)
  if (options.ratingGte) params.append('rating_gte', options.ratingGte)
  if (options.certification) params.append('certification', options.certification)
  if (options.sortBy) params.append('sort_by', options.sortBy)

  const response = await api.get(`/discover/movies?${params}`)
  return response
},

/**
 * Discover shows with filters
 * @param {Object} options - Filter options
 */
async discoverShows(options = {}) {
  const params = new URLSearchParams()
  if (options.page) params.append('page', options.page)
  if (options.genre) params.append('genre', options.genre)
  if (options.year) params.append('year', options.year)
  if (options.yearGte) params.append('year_gte', options.yearGte)
  if (options.yearLte) params.append('year_lte', options.yearLte)
  if (options.ratingGte) params.append('rating_gte', options.ratingGte)
  if (options.sortBy) params.append('sort_by', options.sortBy)

  const response = await api.get(`/discover/shows?${params}`)
  return response
}
```

**Step 2: Commit**

```bash
git add frontend/src/services/discover.js
git commit -m "feat(discovery): add filter methods to frontend service"
```

---

## Task 5: Filter Panel Component

**Files:**
- Create: `frontend/src/components/FilterPanel.vue`

**Step 1: Create the component**

Create `frontend/src/components/FilterPanel.vue`:

```vue
<template>
  <div class="filter-panel" :class="{ open: isOpen }">
    <button class="filter-toggle" @click="isOpen = !isOpen">
      <span>Filters</span>
      <span class="toggle-icon">{{ isOpen ? '▼' : '▶' }}</span>
    </button>

    <div v-if="isOpen" class="filter-content">
      <!-- Genre Filter -->
      <div class="filter-group">
        <label>Genre</label>
        <div class="genre-chips">
          <button
            v-for="genre in genres"
            :key="genre.id"
            :class="['chip', { active: selectedGenres.includes(genre.id) }]"
            @click="toggleGenre(genre.id)"
          >
            {{ genre.name }}
          </button>
        </div>
      </div>

      <!-- Year Filter -->
      <div class="filter-group">
        <label>Year Range</label>
        <div class="range-inputs">
          <input
            type="number"
            v-model.number="filters.yearGte"
            :min="1900"
            :max="currentYear + 1"
            placeholder="From"
          />
          <span>to</span>
          <input
            type="number"
            v-model.number="filters.yearLte"
            :min="1900"
            :max="currentYear + 1"
            placeholder="To"
          />
        </div>
      </div>

      <!-- Rating Filter -->
      <div class="filter-group">
        <label>Minimum Rating: {{ filters.ratingGte || 'Any' }}</label>
        <input
          type="range"
          v-model.number="filters.ratingGte"
          min="0"
          max="10"
          step="0.5"
        />
      </div>

      <!-- Content Rating Filter (Movies only) -->
      <div v-if="mediaType === 'movie'" class="filter-group">
        <label>Content Rating</label>
        <select v-model="filters.certification">
          <option value="">Any</option>
          <option value="G">G</option>
          <option value="PG">PG</option>
          <option value="PG-13">PG-13</option>
          <option value="R">R</option>
        </select>
      </div>

      <!-- Sort By -->
      <div class="filter-group">
        <label>Sort By</label>
        <select v-model="filters.sortBy">
          <option value="popularity.desc">Most Popular</option>
          <option value="vote_average.desc">Highest Rated</option>
          <option value="primary_release_date.desc">Newest</option>
          <option value="primary_release_date.asc">Oldest</option>
        </select>
      </div>

      <!-- Actions -->
      <div class="filter-actions">
        <button class="btn-apply" @click="applyFilters">Apply Filters</button>
        <button class="btn-clear" @click="clearFilters">Clear All</button>
      </div>

      <!-- Active Filters Display -->
      <div v-if="hasActiveFilters" class="active-filters">
        <span
          v-for="filter in activeFilterChips"
          :key="filter.key"
          class="active-chip"
          @click="removeFilter(filter.key)"
        >
          {{ filter.label }} ✕
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import discoverService from '@/services/discover'

const props = defineProps({
  mediaType: {
    type: String,
    default: 'movie'
  }
})

const emit = defineEmits(['filter-change'])

const isOpen = ref(false)
const genres = ref([])
const selectedGenres = ref([])
const currentYear = new Date().getFullYear()

const filters = reactive({
  yearGte: null,
  yearLte: null,
  ratingGte: null,
  certification: '',
  sortBy: 'popularity.desc'
})

onMounted(async () => {
  await loadGenres()
})

watch(() => props.mediaType, async () => {
  await loadGenres()
  selectedGenres.value = []
})

async function loadGenres() {
  try {
    if (props.mediaType === 'movie') {
      genres.value = await discoverService.getMovieGenres()
    } else {
      genres.value = await discoverService.getTvGenres()
    }
  } catch (error) {
    console.error('Failed to load genres:', error)
  }
}

function toggleGenre(genreId) {
  const index = selectedGenres.value.indexOf(genreId)
  if (index === -1) {
    selectedGenres.value.push(genreId)
  } else {
    selectedGenres.value.splice(index, 1)
  }
}

const hasActiveFilters = computed(() => {
  return (
    selectedGenres.value.length > 0 ||
    filters.yearGte ||
    filters.yearLte ||
    filters.ratingGte ||
    filters.certification ||
    filters.sortBy !== 'popularity.desc'
  )
})

const activeFilterChips = computed(() => {
  const chips = []

  if (selectedGenres.value.length > 0) {
    const genreNames = selectedGenres.value
      .map(id => genres.value.find(g => g.id === id)?.name)
      .filter(Boolean)
      .join(', ')
    chips.push({ key: 'genre', label: `Genre: ${genreNames}` })
  }

  if (filters.yearGte || filters.yearLte) {
    const yearLabel = filters.yearGte && filters.yearLte
      ? `${filters.yearGte}-${filters.yearLte}`
      : filters.yearGte
        ? `After ${filters.yearGte}`
        : `Before ${filters.yearLte}`
    chips.push({ key: 'year', label: `Year: ${yearLabel}` })
  }

  if (filters.ratingGte) {
    chips.push({ key: 'rating', label: `Rating: ${filters.ratingGte}+` })
  }

  if (filters.certification) {
    chips.push({ key: 'certification', label: `Rated: ${filters.certification}` })
  }

  if (filters.sortBy !== 'popularity.desc') {
    const sortLabels = {
      'vote_average.desc': 'Highest Rated',
      'primary_release_date.desc': 'Newest',
      'primary_release_date.asc': 'Oldest'
    }
    chips.push({ key: 'sort', label: `Sort: ${sortLabels[filters.sortBy]}` })
  }

  return chips
})

function removeFilter(key) {
  if (key === 'genre') {
    selectedGenres.value = []
  } else if (key === 'year') {
    filters.yearGte = null
    filters.yearLte = null
  } else if (key === 'rating') {
    filters.ratingGte = null
  } else if (key === 'certification') {
    filters.certification = ''
  } else if (key === 'sort') {
    filters.sortBy = 'popularity.desc'
  }
  applyFilters()
}

function applyFilters() {
  emit('filter-change', {
    genre: selectedGenres.value.join(',') || null,
    yearGte: filters.yearGte,
    yearLte: filters.yearLte,
    ratingGte: filters.ratingGte,
    certification: filters.certification || null,
    sortBy: filters.sortBy
  })
}

function clearFilters() {
  selectedGenres.value = []
  filters.yearGte = null
  filters.yearLte = null
  filters.ratingGte = null
  filters.certification = ''
  filters.sortBy = 'popularity.desc'
  applyFilters()
}
</script>

<style scoped>
.filter-panel {
  background: #1a1a2e;
  border-radius: 8px;
  margin-bottom: 1rem;
}

.filter-toggle {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: none;
  border: none;
  color: #fff;
  font-size: 1rem;
  cursor: pointer;
}

.filter-content {
  padding: 0 1rem 1rem;
}

.filter-group {
  margin-bottom: 1rem;
}

.filter-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: #ccc;
  font-size: 0.9rem;
}

.genre-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.chip {
  padding: 0.5rem 1rem;
  border: 1px solid #333;
  border-radius: 20px;
  background: transparent;
  color: #ccc;
  cursor: pointer;
  font-size: 0.85rem;
}

.chip.active {
  background: #e94560;
  border-color: #e94560;
  color: #fff;
}

.chip:hover:not(.active) {
  border-color: #e94560;
}

.range-inputs {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.range-inputs input {
  width: 100px;
  padding: 0.5rem;
  border: 1px solid #333;
  border-radius: 4px;
  background: #0f0f1a;
  color: #fff;
}

.range-inputs span {
  color: #ccc;
}

input[type="range"] {
  width: 100%;
  accent-color: #e94560;
}

select {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #333;
  border-radius: 4px;
  background: #0f0f1a;
  color: #fff;
}

.filter-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
}

.btn-apply {
  flex: 1;
  padding: 0.75rem;
  border: none;
  border-radius: 4px;
  background: #e94560;
  color: #fff;
  cursor: pointer;
}

.btn-clear {
  padding: 0.75rem 1rem;
  border: 1px solid #333;
  border-radius: 4px;
  background: transparent;
  color: #ccc;
  cursor: pointer;
}

.active-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #333;
}

.active-chip {
  padding: 0.25rem 0.75rem;
  background: #252540;
  border-radius: 20px;
  color: #fff;
  font-size: 0.8rem;
  cursor: pointer;
}

.active-chip:hover {
  background: #e94560;
}
</style>
```

**Step 2: Commit**

```bash
git add frontend/src/components/FilterPanel.vue
git commit -m "feat(discovery): add FilterPanel component"
```

---

## Task 6: Integrate Filters into DiscoverView

**Files:**
- Modify: `frontend/src/views/DiscoverView.vue`

**Step 1: Update DiscoverView**

Modify `frontend/src/views/DiscoverView.vue`:

```vue
<template>
  <div class="discover-view">
    <!-- Media Type Tabs -->
    <div class="media-tabs">
      <button
        :class="['tab', { active: mediaType === 'movie' }]"
        @click="switchMediaType('movie')"
      >
        Movies
      </button>
      <button
        :class="['tab', { active: mediaType === 'tv' }]"
        @click="switchMediaType('tv')"
      >
        TV Shows
      </button>
    </div>

    <!-- Search Bar -->
    <div class="search-bar">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Search..."
        @input="handleSearchInput"
      />
    </div>

    <!-- Filter Panel -->
    <FilterPanel
      :media-type="mediaType"
      @filter-change="handleFilterChange"
    />

    <!-- Results -->
    <div class="results-grid">
      <MediaCard
        v-for="item in results"
        :key="item.id"
        :media="item"
        :media-type="mediaType"
      />
    </div>

    <!-- Load More -->
    <button
      v-if="hasMore"
      class="load-more"
      @click="loadMore"
      :disabled="loading"
    >
      {{ loading ? 'Loading...' : 'Load More' }}
    </button>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import discoverService from '@/services/discover'
import MediaCard from '@/components/MediaCard.vue'
import FilterPanel from '@/components/FilterPanel.vue'

const mediaType = ref('movie')
const searchQuery = ref('')
const results = ref([])
const loading = ref(false)
const page = ref(1)
const hasMore = ref(true)

const filters = reactive({
  genre: null,
  yearGte: null,
  yearLte: null,
  ratingGte: null,
  certification: null,
  sortBy: 'popularity.desc'
})

let searchTimeout = null

onMounted(async () => {
  await fetchResults()
})

async function fetchResults(append = false) {
  loading.value = true

  try {
    let data

    if (searchQuery.value.trim()) {
      // Search mode - filters not applied
      if (mediaType.value === 'movie') {
        data = await discoverService.searchMovies(searchQuery.value, page.value)
      } else {
        data = await discoverService.searchShows(searchQuery.value, page.value)
      }
    } else {
      // Discovery mode with filters
      const options = {
        page: page.value,
        ...filters
      }

      if (mediaType.value === 'movie') {
        data = await discoverService.discoverMovies(options)
      } else {
        data = await discoverService.discoverShows(options)
      }
    }

    if (append) {
      results.value = [...results.value, ...data.results]
    } else {
      results.value = data.results
    }

    hasMore.value = page.value < data.total_pages
  } catch (error) {
    console.error('Failed to fetch results:', error)
  } finally {
    loading.value = false
  }
}

function handleSearchInput() {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    page.value = 1
    fetchResults()
  }, 300)
}

function handleFilterChange(newFilters) {
  Object.assign(filters, newFilters)
  page.value = 1
  fetchResults()
}

function switchMediaType(type) {
  mediaType.value = type
  page.value = 1
  searchQuery.value = ''
  fetchResults()
}

function loadMore() {
  page.value++
  fetchResults(true)
}
</script>
```

**Step 2: Commit**

```bash
git add frontend/src/views/DiscoverView.vue
git commit -m "feat(discovery): integrate filter panel into DiscoverView"
```

---

## Task 7: Final Testing

**Step 1: Run all backend tests**

```bash
cd backend && pytest -v
```
Expected: All tests pass

**Step 2: Manual testing**

1. Start servers: `start.bat`
2. Open http://localhost:3000
3. Test filters:
   - Select genres - results should filter
   - Set year range - results should filter
   - Adjust rating slider - results should filter
   - Change sort order - results should reorder
4. Switch between Movies/TV - genres should update
5. Clear filters - should return to trending

**Step 3: Final commit**

```bash
git add -A
git commit -m "feat(discovery): complete filter system with genre, year, rating filters"
```

---

## Summary

| Task | Description |
|------|-------------|
| 1 | Genre list endpoints |
| 2 | Filter parameters schema |
| 3 | Filtered discovery endpoints |
| 4 | Frontend genre service |
| 5 | FilterPanel component |
| 6 | DiscoverView integration |
| 7 | Testing |
