# Media Deep Dive Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add person pages, media detail view, collections, trailers, and "More Like This" recommendations.

**Architecture:** New detail endpoints wrapping TMDB API. Frontend detail pages with modals for trailers. Cast/crew links to person pages.

**Tech Stack:** FastAPI, TMDB API, Vue 3, Vue Router, YouTube iframe embed

---

## Task 1: Person Endpoint

**Files:**
- Modify: `backend/src/app/modules/discovery/client.py`
- Modify: `backend/src/app/modules/discovery/router.py`
- Create: `backend/tests/test_person_endpoint.py`

**Step 1: Write the failing test**

Create `backend/tests/test_person_endpoint.py`:

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_get_person():
    """GET /api/person/{id} should return person details."""
    # Tom Hanks ID: 31
    response = client.get("/api/person/31")
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "name" in data
    assert "biography" in data
    assert "combined_credits" in data


def test_get_person_not_found():
    """GET /api/person/{id} should return 404 for invalid ID."""
    response = client.get("/api/person/999999999")
    assert response.status_code == 404
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_person_endpoint.py -v`
Expected: FAIL with 404 (route not found)

**Step 3: Write minimal implementation**

Add to `backend/src/app/modules/discovery/client.py`:

```python
async def get_person(self, person_id: int) -> dict:
    """Get person details with combined credits."""
    url = f"{self.base_url}/person/{person_id}"
    params = {
        "api_key": self.api_key,
        "append_to_response": "combined_credits"
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()
```

Add to `backend/src/app/modules/discovery/router.py`:

```python
from fastapi import HTTPException

@router.get("/person/{person_id}")
async def get_person(person_id: int):
    """Get person details with filmography."""
    client = TMDBClient()
    data = await client.get_person(person_id)
    if not data:
        raise HTTPException(status_code=404, detail="Person not found")
    return data
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_person_endpoint.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/app/modules/discovery/client.py
git add backend/src/app/modules/discovery/router.py
git add backend/tests/test_person_endpoint.py
git commit -m "feat(media): add person details endpoint"
```

---

## Task 2: Movie Detail Endpoint

**Files:**
- Modify: `backend/src/app/modules/discovery/client.py`
- Modify: `backend/src/app/modules/discovery/router.py`
- Create: `backend/tests/test_movie_detail_endpoint.py`

**Step 1: Write the failing test**

Create `backend/tests/test_movie_detail_endpoint.py`:

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_get_movie_detail():
    """GET /api/movies/{id} should return movie details."""
    # The Matrix ID: 603
    response = client.get("/api/movies/603")
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "title" in data
    assert "overview" in data
    assert "credits" in data
    assert "videos" in data


def test_get_movie_not_found():
    """GET /api/movies/{id} should return 404 for invalid ID."""
    response = client.get("/api/movies/999999999")
    assert response.status_code == 404
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_movie_detail_endpoint.py -v`
Expected: FAIL with 404

**Step 3: Write minimal implementation**

Add to `backend/src/app/modules/discovery/client.py`:

```python
async def get_movie_detail(self, movie_id: int) -> dict:
    """Get movie details with credits and videos."""
    url = f"{self.base_url}/movie/{movie_id}"
    params = {
        "api_key": self.api_key,
        "append_to_response": "credits,videos,recommendations"
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()
```

Add to `backend/src/app/modules/discovery/router.py`:

```python
@router.get("/movies/{movie_id}")
async def get_movie_detail(movie_id: int):
    """Get movie details with cast, videos, recommendations."""
    client = TMDBClient()
    data = await client.get_movie_detail(movie_id)
    if not data:
        raise HTTPException(status_code=404, detail="Movie not found")
    return data
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_movie_detail_endpoint.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/app/modules/discovery/client.py
git add backend/src/app/modules/discovery/router.py
git add backend/tests/test_movie_detail_endpoint.py
git commit -m "feat(media): add movie detail endpoint with credits and videos"
```

---

## Task 3: Show Detail Endpoint

**Files:**
- Modify: `backend/src/app/modules/discovery/client.py`
- Modify: `backend/src/app/modules/discovery/router.py`
- Create: `backend/tests/test_show_detail_endpoint.py`

**Step 1: Write the failing test**

Create `backend/tests/test_show_detail_endpoint.py`:

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_get_show_detail():
    """GET /api/shows/{id} should return show details."""
    # Breaking Bad ID: 1396
    response = client.get("/api/shows/1396")
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "name" in data
    assert "overview" in data
    assert "credits" in data
    assert "videos" in data


def test_get_show_not_found():
    """GET /api/shows/{id} should return 404 for invalid ID."""
    response = client.get("/api/shows/999999999")
    assert response.status_code == 404
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_show_detail_endpoint.py -v`
Expected: FAIL with 404

**Step 3: Write minimal implementation**

Add to `backend/src/app/modules/discovery/client.py`:

```python
async def get_show_detail(self, show_id: int) -> dict:
    """Get TV show details with credits and videos."""
    url = f"{self.base_url}/tv/{show_id}"
    params = {
        "api_key": self.api_key,
        "append_to_response": "credits,videos,recommendations"
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()
```

Add to `backend/src/app/modules/discovery/router.py`:

```python
@router.get("/shows/{show_id}")
async def get_show_detail(show_id: int):
    """Get TV show details with cast, videos, recommendations."""
    client = TMDBClient()
    data = await client.get_show_detail(show_id)
    if not data:
        raise HTTPException(status_code=404, detail="Show not found")
    return data
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_show_detail_endpoint.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/app/modules/discovery/client.py
git add backend/src/app/modules/discovery/router.py
git add backend/tests/test_show_detail_endpoint.py
git commit -m "feat(media): add show detail endpoint with credits and videos"
```

---

## Task 4: Collection Endpoint

**Files:**
- Modify: `backend/src/app/modules/discovery/client.py`
- Modify: `backend/src/app/modules/discovery/router.py`
- Create: `backend/tests/test_collection_endpoint.py`

**Step 1: Write the failing test**

Create `backend/tests/test_collection_endpoint.py`:

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_get_collection():
    """GET /api/collection/{id} should return collection details."""
    # The Matrix Collection ID: 2344
    response = client.get("/api/collection/2344")
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "name" in data
    assert "parts" in data
    assert isinstance(data["parts"], list)


def test_get_collection_not_found():
    """GET /api/collection/{id} should return 404 for invalid ID."""
    response = client.get("/api/collection/999999999")
    assert response.status_code == 404
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_collection_endpoint.py -v`
Expected: FAIL with 404

**Step 3: Write minimal implementation**

Add to `backend/src/app/modules/discovery/client.py`:

```python
async def get_collection(self, collection_id: int) -> dict:
    """Get collection details with all movies."""
    url = f"{self.base_url}/collection/{collection_id}"
    params = {"api_key": self.api_key}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()
```

Add to `backend/src/app/modules/discovery/router.py`:

```python
@router.get("/collection/{collection_id}")
async def get_collection(collection_id: int):
    """Get collection details with all movies in the collection."""
    client = TMDBClient()
    data = await client.get_collection(collection_id)
    if not data:
        raise HTTPException(status_code=404, detail="Collection not found")
    return data
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_collection_endpoint.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/app/modules/discovery/client.py
git add backend/src/app/modules/discovery/router.py
git add backend/tests/test_collection_endpoint.py
git commit -m "feat(media): add collection endpoint"
```

---

## Task 5: Frontend Media Service Updates

**Files:**
- Modify: `frontend/src/services/discover.js`

**Step 1: Add detail methods**

Add to `frontend/src/services/discover.js`:

```javascript
/**
 * Get person details with filmography
 * @param {number} personId - TMDB person ID
 */
async getPerson(personId) {
  const response = await api.get(`/person/${personId}`)
  return response
},

/**
 * Get movie details with credits, videos, recommendations
 * @param {number} movieId - TMDB movie ID
 */
async getMovieDetail(movieId) {
  const response = await api.get(`/movies/${movieId}`)
  return response
},

/**
 * Get TV show details with credits, videos, recommendations
 * @param {number} showId - TMDB show ID
 */
async getShowDetail(showId) {
  const response = await api.get(`/shows/${showId}`)
  return response
},

/**
 * Get collection details
 * @param {number} collectionId - TMDB collection ID
 */
async getCollection(collectionId) {
  const response = await api.get(`/collection/${collectionId}`)
  return response
}
```

**Step 2: Commit**

```bash
git add frontend/src/services/discover.js
git commit -m "feat(media): add detail methods to frontend service"
```

---

## Task 6: TrailerModal Component

**Files:**
- Create: `frontend/src/components/TrailerModal.vue`

**Step 1: Create the component**

Create `frontend/src/components/TrailerModal.vue`:

```vue
<template>
  <Teleport to="body">
    <div v-if="isOpen" class="modal-overlay" @click="close">
      <div class="modal-content" @click.stop>
        <button class="close-btn" @click="close">✕</button>
        <div class="video-container">
          <iframe
            v-if="videoKey"
            :src="`https://www.youtube.com/embed/${videoKey}?autoplay=1`"
            frameborder="0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowfullscreen
          ></iframe>
          <div v-else class="no-trailer">
            No trailer available
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  videos: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['close'])

const videoKey = computed(() => {
  // Find the first YouTube trailer
  const trailer = props.videos?.find(
    v => v.site === 'YouTube' && (v.type === 'Trailer' || v.type === 'Teaser')
  )
  return trailer?.key || null
})

function close() {
  emit('close')
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  position: relative;
  width: 90%;
  max-width: 900px;
}

.close-btn {
  position: absolute;
  top: -40px;
  right: 0;
  background: none;
  border: none;
  color: #fff;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0.5rem;
}

.video-container {
  position: relative;
  padding-bottom: 56.25%; /* 16:9 aspect ratio */
  height: 0;
  overflow: hidden;
  background: #000;
  border-radius: 8px;
}

.video-container iframe {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

.no-trailer {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: #666;
  font-size: 1.2rem;
}
</style>
```

**Step 2: Commit**

```bash
git add frontend/src/components/TrailerModal.vue
git commit -m "feat(media): add TrailerModal component"
```

---

## Task 7: CastCarousel Component

**Files:**
- Create: `frontend/src/components/CastCarousel.vue`

**Step 1: Create the component**

Create `frontend/src/components/CastCarousel.vue`:

```vue
<template>
  <div class="cast-carousel">
    <h3>{{ title }}</h3>
    <div class="carousel-container">
      <div class="carousel-scroll">
        <router-link
          v-for="person in cast"
          :key="person.id"
          :to="`/person/${person.id}`"
          class="cast-card"
        >
          <div class="cast-image">
            <img
              v-if="person.profile_path"
              :src="`https://image.tmdb.org/t/p/w185${person.profile_path}`"
              :alt="person.name"
            />
            <div v-else class="no-image">
              {{ person.name.charAt(0) }}
            </div>
          </div>
          <div class="cast-info">
            <div class="cast-name">{{ person.name }}</div>
            <div class="cast-role">{{ person.character || person.job }}</div>
          </div>
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    default: 'Cast'
  },
  cast: {
    type: Array,
    default: () => []
  }
})
</script>

<style scoped>
.cast-carousel {
  margin: 2rem 0;
}

.cast-carousel h3 {
  margin-bottom: 1rem;
  color: #fff;
}

.carousel-container {
  overflow: hidden;
}

.carousel-scroll {
  display: flex;
  gap: 1rem;
  overflow-x: auto;
  padding-bottom: 1rem;
  scrollbar-width: thin;
  scrollbar-color: #333 transparent;
}

.carousel-scroll::-webkit-scrollbar {
  height: 8px;
}

.carousel-scroll::-webkit-scrollbar-track {
  background: transparent;
}

.carousel-scroll::-webkit-scrollbar-thumb {
  background: #333;
  border-radius: 4px;
}

.cast-card {
  flex: 0 0 auto;
  width: 120px;
  text-decoration: none;
  color: inherit;
}

.cast-card:hover .cast-name {
  color: #e94560;
}

.cast-image {
  width: 120px;
  height: 180px;
  border-radius: 8px;
  overflow: hidden;
  background: #1a1a2e;
}

.cast-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.no-image {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #252540;
  color: #666;
  font-size: 2rem;
}

.cast-info {
  padding: 0.5rem 0;
}

.cast-name {
  font-size: 0.9rem;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cast-role {
  font-size: 0.8rem;
  color: #999;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
```

**Step 2: Commit**

```bash
git add frontend/src/components/CastCarousel.vue
git commit -m "feat(media): add CastCarousel component"
```

---

## Task 8: MediaCarousel Component

**Files:**
- Create: `frontend/src/components/MediaCarousel.vue`

**Step 1: Create the component**

Create `frontend/src/components/MediaCarousel.vue`:

```vue
<template>
  <div class="media-carousel">
    <h3>{{ title }}</h3>
    <div class="carousel-container">
      <div class="carousel-scroll">
        <router-link
          v-for="item in items"
          :key="item.id"
          :to="`/${mediaType}/${item.id}`"
          class="media-card-small"
        >
          <div class="poster">
            <img
              v-if="item.poster_path"
              :src="`https://image.tmdb.org/t/p/w185${item.poster_path}`"
              :alt="item.title || item.name"
            />
            <div v-else class="no-poster">
              {{ (item.title || item.name).charAt(0) }}
            </div>
          </div>
          <div class="media-title">{{ item.title || item.name }}</div>
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    default: 'Recommendations'
  },
  items: {
    type: Array,
    default: () => []
  },
  mediaType: {
    type: String,
    default: 'movie'
  }
})
</script>

<style scoped>
.media-carousel {
  margin: 2rem 0;
}

.media-carousel h3 {
  margin-bottom: 1rem;
  color: #fff;
}

.carousel-container {
  overflow: hidden;
}

.carousel-scroll {
  display: flex;
  gap: 1rem;
  overflow-x: auto;
  padding-bottom: 1rem;
  scrollbar-width: thin;
  scrollbar-color: #333 transparent;
}

.media-card-small {
  flex: 0 0 auto;
  width: 130px;
  text-decoration: none;
  color: inherit;
}

.media-card-small:hover .media-title {
  color: #e94560;
}

.poster {
  width: 130px;
  height: 195px;
  border-radius: 8px;
  overflow: hidden;
  background: #1a1a2e;
}

.poster img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.no-poster {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #252540;
  color: #666;
  font-size: 2rem;
}

.media-title {
  padding: 0.5rem 0;
  font-size: 0.85rem;
  color: #ccc;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
```

**Step 2: Commit**

```bash
git add frontend/src/components/MediaCarousel.vue
git commit -m "feat(media): add MediaCarousel component for recommendations"
```

---

## Task 9: MediaDetailView

**Files:**
- Create: `frontend/src/views/MediaDetailView.vue`
- Modify: `frontend/src/router/index.js`

**Step 1: Create the view**

Create `frontend/src/views/MediaDetailView.vue`:

```vue
<template>
  <div class="media-detail-view" v-if="media">
    <!-- Backdrop -->
    <div
      class="backdrop"
      :style="backdropStyle"
    ></div>

    <!-- Content -->
    <div class="content">
      <!-- Poster & Info -->
      <div class="main-info">
        <div class="poster">
          <img
            v-if="media.poster_path"
            :src="`https://image.tmdb.org/t/p/w342${media.poster_path}`"
            :alt="title"
          />
        </div>

        <div class="info">
          <h1>{{ title }}</h1>

          <div class="meta">
            <span v-if="releaseYear">{{ releaseYear }}</span>
            <span v-if="runtime">{{ runtime }}</span>
            <span v-if="rating" class="rating">★ {{ rating }}</span>
          </div>

          <div v-if="genres.length" class="genres">
            <span v-for="genre in genres" :key="genre.id" class="genre-tag">
              {{ genre.name }}
            </span>
          </div>

          <p class="overview">{{ media.overview }}</p>

          <!-- Collection Link -->
          <router-link
            v-if="media.belongs_to_collection"
            :to="`/collection/${media.belongs_to_collection.id}`"
            class="collection-link"
          >
            Part of {{ media.belongs_to_collection.name }}
          </router-link>

          <!-- Actions -->
          <div class="actions">
            <button
              v-if="hasTrailer"
              class="btn-trailer"
              @click="showTrailer = true"
            >
              ▶ Watch Trailer
            </button>
            <button class="btn-add" @click="addToWatchlist">
              + Add to Watchlist
            </button>
          </div>
        </div>
      </div>

      <!-- Cast -->
      <CastCarousel
        v-if="cast.length"
        title="Cast"
        :cast="cast"
      />

      <!-- Recommendations -->
      <MediaCarousel
        v-if="recommendations.length"
        title="More Like This"
        :items="recommendations"
        :media-type="mediaType"
      />
    </div>

    <!-- Trailer Modal -->
    <TrailerModal
      :is-open="showTrailer"
      :videos="media.videos?.results || []"
      @close="showTrailer = false"
    />
  </div>

  <div v-else-if="loading" class="loading">
    Loading...
  </div>

  <div v-else class="error">
    Media not found
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import discoverService from '@/services/discover'
import CastCarousel from '@/components/CastCarousel.vue'
import MediaCarousel from '@/components/MediaCarousel.vue'
import TrailerModal from '@/components/TrailerModal.vue'

const route = useRoute()
const media = ref(null)
const loading = ref(true)
const showTrailer = ref(false)

const mediaType = computed(() => route.params.type || 'movie')
const mediaId = computed(() => route.params.id)

const title = computed(() => media.value?.title || media.value?.name || '')
const releaseYear = computed(() => {
  const date = media.value?.release_date || media.value?.first_air_date
  return date ? new Date(date).getFullYear() : null
})
const runtime = computed(() => {
  if (media.value?.runtime) {
    const hours = Math.floor(media.value.runtime / 60)
    const mins = media.value.runtime % 60
    return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`
  }
  return null
})
const rating = computed(() => {
  return media.value?.vote_average
    ? media.value.vote_average.toFixed(1)
    : null
})
const genres = computed(() => media.value?.genres || [])
const cast = computed(() => media.value?.credits?.cast?.slice(0, 20) || [])
const recommendations = computed(() =>
  media.value?.recommendations?.results?.slice(0, 10) || []
)
const hasTrailer = computed(() =>
  media.value?.videos?.results?.some(
    v => v.site === 'YouTube' && (v.type === 'Trailer' || v.type === 'Teaser')
  )
)
const backdropStyle = computed(() => ({
  backgroundImage: media.value?.backdrop_path
    ? `url(https://image.tmdb.org/t/p/w1280${media.value.backdrop_path})`
    : 'none'
}))

onMounted(async () => {
  await fetchMedia()
})

watch(() => route.params, async () => {
  await fetchMedia()
})

async function fetchMedia() {
  loading.value = true
  media.value = null

  try {
    if (mediaType.value === 'movie') {
      media.value = await discoverService.getMovieDetail(mediaId.value)
    } else {
      media.value = await discoverService.getShowDetail(mediaId.value)
    }
  } catch (error) {
    console.error('Failed to fetch media:', error)
  } finally {
    loading.value = false
  }
}

async function addToWatchlist() {
  // TODO: Integrate with watchlist service
  console.log('Add to watchlist:', mediaId.value)
}
</script>

<style scoped>
.media-detail-view {
  position: relative;
  min-height: 100vh;
}

.backdrop {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 500px;
  background-size: cover;
  background-position: center top;
  opacity: 0.3;
  mask-image: linear-gradient(to bottom, black, transparent);
  -webkit-mask-image: linear-gradient(to bottom, black, transparent);
}

.content {
  position: relative;
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

.main-info {
  display: flex;
  gap: 2rem;
  margin-bottom: 2rem;
}

.poster {
  flex: 0 0 auto;
}

.poster img {
  width: 250px;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
}

.info {
  flex: 1;
}

.info h1 {
  font-size: 2.5rem;
  margin: 0 0 1rem;
  color: #fff;
}

.meta {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
  color: #999;
}

.rating {
  color: #ffc107;
}

.genres {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.genre-tag {
  padding: 0.25rem 0.75rem;
  background: #252540;
  border-radius: 20px;
  font-size: 0.85rem;
  color: #ccc;
}

.overview {
  color: #ccc;
  line-height: 1.6;
  margin-bottom: 1rem;
}

.collection-link {
  display: inline-block;
  color: #e94560;
  margin-bottom: 1rem;
}

.actions {
  display: flex;
  gap: 1rem;
  margin-top: 1.5rem;
}

.btn-trailer {
  padding: 0.75rem 1.5rem;
  background: #e94560;
  border: none;
  border-radius: 4px;
  color: #fff;
  font-size: 1rem;
  cursor: pointer;
}

.btn-add {
  padding: 0.75rem 1.5rem;
  background: transparent;
  border: 1px solid #e94560;
  border-radius: 4px;
  color: #e94560;
  font-size: 1rem;
  cursor: pointer;
}

.loading, .error {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 50vh;
  color: #666;
  font-size: 1.2rem;
}

@media (max-width: 768px) {
  .main-info {
    flex-direction: column;
    align-items: center;
    text-align: center;
  }

  .genres {
    justify-content: center;
  }

  .actions {
    justify-content: center;
  }
}
</style>
```

**Step 2: Add routes**

Modify `frontend/src/router/index.js`:

```javascript
// Add import
import MediaDetailView from '@/views/MediaDetailView.vue'

// Add routes
{
  path: '/movie/:id',
  name: 'MovieDetail',
  component: MediaDetailView,
  props: route => ({ type: 'movie', id: route.params.id })
},
{
  path: '/tv/:id',
  name: 'ShowDetail',
  component: MediaDetailView,
  props: route => ({ type: 'tv', id: route.params.id })
}
```

**Step 3: Commit**

```bash
git add frontend/src/views/MediaDetailView.vue
git add frontend/src/router/index.js
git commit -m "feat(media): add MediaDetailView with trailer and recommendations"
```

---

## Task 10: PersonView

**Files:**
- Create: `frontend/src/views/PersonView.vue`
- Modify: `frontend/src/router/index.js`

**Step 1: Create the view**

Create `frontend/src/views/PersonView.vue`:

```vue
<template>
  <div class="person-view" v-if="person">
    <div class="person-header">
      <div class="person-image">
        <img
          v-if="person.profile_path"
          :src="`https://image.tmdb.org/t/p/w300${person.profile_path}`"
          :alt="person.name"
        />
        <div v-else class="no-image">
          {{ person.name.charAt(0) }}
        </div>
      </div>

      <div class="person-info">
        <h1>{{ person.name }}</h1>
        <p v-if="person.birthday" class="meta">
          Born: {{ formatDate(person.birthday) }}
          <span v-if="person.place_of_birth"> in {{ person.place_of_birth }}</span>
        </p>
        <p v-if="person.biography" class="biography">
          {{ truncatedBio }}
          <button v-if="person.biography.length > 500" @click="showFullBio = !showFullBio">
            {{ showFullBio ? 'Show less' : 'Read more' }}
          </button>
        </p>
      </div>
    </div>

    <div class="filmography">
      <h2>Known For</h2>

      <div class="tabs">
        <button
          :class="['tab', { active: activeTab === 'movies' }]"
          @click="activeTab = 'movies'"
        >
          Movies ({{ movies.length }})
        </button>
        <button
          :class="['tab', { active: activeTab === 'tv' }]"
          @click="activeTab = 'tv'"
        >
          TV Shows ({{ tvShows.length }})
        </button>
      </div>

      <div class="credits-grid">
        <router-link
          v-for="item in activeCredits"
          :key="`${item.media_type}-${item.id}`"
          :to="`/${item.media_type === 'movie' ? 'movie' : 'tv'}/${item.id}`"
          class="credit-card"
        >
          <div class="credit-poster">
            <img
              v-if="item.poster_path"
              :src="`https://image.tmdb.org/t/p/w185${item.poster_path}`"
              :alt="item.title || item.name"
            />
            <div v-else class="no-poster">?</div>
          </div>
          <div class="credit-info">
            <div class="credit-title">{{ item.title || item.name }}</div>
            <div class="credit-role">{{ item.character || item.job }}</div>
            <div class="credit-year">{{ getYear(item) }}</div>
          </div>
        </router-link>
      </div>
    </div>
  </div>

  <div v-else-if="loading" class="loading">Loading...</div>
  <div v-else class="error">Person not found</div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import discoverService from '@/services/discover'

const route = useRoute()
const person = ref(null)
const loading = ref(true)
const showFullBio = ref(false)
const activeTab = ref('movies')

const personId = computed(() => route.params.id)

const truncatedBio = computed(() => {
  if (!person.value?.biography) return ''
  if (showFullBio.value || person.value.biography.length <= 500) {
    return person.value.biography
  }
  return person.value.biography.slice(0, 500) + '...'
})

const movies = computed(() => {
  const credits = person.value?.combined_credits?.cast || []
  return credits
    .filter(c => c.media_type === 'movie')
    .sort((a, b) => (b.popularity || 0) - (a.popularity || 0))
})

const tvShows = computed(() => {
  const credits = person.value?.combined_credits?.cast || []
  return credits
    .filter(c => c.media_type === 'tv')
    .sort((a, b) => (b.popularity || 0) - (a.popularity || 0))
})

const activeCredits = computed(() => {
  return activeTab.value === 'movies' ? movies.value : tvShows.value
})

onMounted(async () => {
  await fetchPerson()
})

watch(() => route.params.id, async () => {
  await fetchPerson()
})

async function fetchPerson() {
  loading.value = true
  person.value = null

  try {
    person.value = await discoverService.getPerson(personId.value)
  } catch (error) {
    console.error('Failed to fetch person:', error)
  } finally {
    loading.value = false
  }
}

function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

function getYear(item) {
  const date = item.release_date || item.first_air_date
  return date ? new Date(date).getFullYear() : ''
}
</script>

<style scoped>
.person-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.person-header {
  display: flex;
  gap: 2rem;
  margin-bottom: 3rem;
}

.person-image {
  flex: 0 0 auto;
}

.person-image img {
  width: 200px;
  border-radius: 8px;
}

.no-image {
  width: 200px;
  height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #252540;
  border-radius: 8px;
  color: #666;
  font-size: 4rem;
}

.person-info h1 {
  margin: 0 0 0.5rem;
  color: #fff;
}

.meta {
  color: #999;
  margin-bottom: 1rem;
}

.biography {
  color: #ccc;
  line-height: 1.6;
}

.biography button {
  background: none;
  border: none;
  color: #e94560;
  cursor: pointer;
  padding: 0;
  margin-left: 0.5rem;
}

.filmography h2 {
  color: #fff;
  margin-bottom: 1rem;
}

.tabs {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
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
  background: #e94560;
  border-color: #e94560;
  color: #fff;
}

.credits-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 1.5rem;
}

.credit-card {
  text-decoration: none;
  color: inherit;
}

.credit-card:hover .credit-title {
  color: #e94560;
}

.credit-poster {
  width: 100%;
  aspect-ratio: 2/3;
  border-radius: 8px;
  overflow: hidden;
  background: #1a1a2e;
}

.credit-poster img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.no-poster {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #666;
  font-size: 2rem;
}

.credit-info {
  padding: 0.5rem 0;
}

.credit-title {
  font-size: 0.9rem;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.credit-role {
  font-size: 0.8rem;
  color: #999;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.credit-year {
  font-size: 0.8rem;
  color: #666;
}

.loading, .error {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 50vh;
  color: #666;
}

@media (max-width: 768px) {
  .person-header {
    flex-direction: column;
    align-items: center;
    text-align: center;
  }
}
</style>
```

**Step 2: Add route**

Add to `frontend/src/router/index.js`:

```javascript
// Add import
import PersonView from '@/views/PersonView.vue'

// Add route
{
  path: '/person/:id',
  name: 'Person',
  component: PersonView
}
```

**Step 3: Commit**

```bash
git add frontend/src/views/PersonView.vue
git add frontend/src/router/index.js
git commit -m "feat(media): add PersonView with filmography"
```

---

## Task 11: CollectionView

**Files:**
- Create: `frontend/src/views/CollectionView.vue`
- Modify: `frontend/src/router/index.js`

**Step 1: Create the view**

Create `frontend/src/views/CollectionView.vue`:

```vue
<template>
  <div class="collection-view" v-if="collection">
    <!-- Backdrop -->
    <div
      class="backdrop"
      :style="backdropStyle"
    ></div>

    <div class="content">
      <div class="collection-header">
        <div class="poster">
          <img
            v-if="collection.poster_path"
            :src="`https://image.tmdb.org/t/p/w300${collection.poster_path}`"
            :alt="collection.name"
          />
        </div>

        <div class="info">
          <h1>{{ collection.name }}</h1>
          <p class="overview">{{ collection.overview }}</p>
          <p class="count">{{ collection.parts?.length || 0 }} movies</p>
        </div>
      </div>

      <div class="movies-grid">
        <router-link
          v-for="movie in sortedMovies"
          :key="movie.id"
          :to="`/movie/${movie.id}`"
          class="movie-card"
        >
          <div class="movie-poster">
            <img
              v-if="movie.poster_path"
              :src="`https://image.tmdb.org/t/p/w185${movie.poster_path}`"
              :alt="movie.title"
            />
            <div v-else class="no-poster">?</div>
          </div>
          <div class="movie-info">
            <div class="movie-title">{{ movie.title }}</div>
            <div class="movie-year">{{ getYear(movie) }}</div>
          </div>
        </router-link>
      </div>
    </div>
  </div>

  <div v-else-if="loading" class="loading">Loading...</div>
  <div v-else class="error">Collection not found</div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import discoverService from '@/services/discover'

const route = useRoute()
const collection = ref(null)
const loading = ref(true)

const collectionId = computed(() => route.params.id)

const backdropStyle = computed(() => ({
  backgroundImage: collection.value?.backdrop_path
    ? `url(https://image.tmdb.org/t/p/w1280${collection.value.backdrop_path})`
    : 'none'
}))

const sortedMovies = computed(() => {
  if (!collection.value?.parts) return []
  return [...collection.value.parts].sort((a, b) => {
    const dateA = a.release_date || '9999'
    const dateB = b.release_date || '9999'
    return dateA.localeCompare(dateB)
  })
})

onMounted(async () => {
  await fetchCollection()
})

watch(() => route.params.id, async () => {
  await fetchCollection()
})

async function fetchCollection() {
  loading.value = true
  collection.value = null

  try {
    collection.value = await discoverService.getCollection(collectionId.value)
  } catch (error) {
    console.error('Failed to fetch collection:', error)
  } finally {
    loading.value = false
  }
}

function getYear(movie) {
  return movie.release_date
    ? new Date(movie.release_date).getFullYear()
    : 'TBA'
}
</script>

<style scoped>
.collection-view {
  position: relative;
  min-height: 100vh;
}

.backdrop {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 400px;
  background-size: cover;
  background-position: center;
  opacity: 0.3;
  mask-image: linear-gradient(to bottom, black, transparent);
  -webkit-mask-image: linear-gradient(to bottom, black, transparent);
}

.content {
  position: relative;
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.collection-header {
  display: flex;
  gap: 2rem;
  margin-bottom: 3rem;
}

.poster img {
  width: 200px;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
}

.info h1 {
  margin: 0 0 1rem;
  color: #fff;
  font-size: 2rem;
}

.overview {
  color: #ccc;
  line-height: 1.6;
  margin-bottom: 1rem;
}

.count {
  color: #999;
}

.movies-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 1.5rem;
}

.movie-card {
  text-decoration: none;
  color: inherit;
}

.movie-card:hover .movie-title {
  color: #e94560;
}

.movie-poster {
  width: 100%;
  aspect-ratio: 2/3;
  border-radius: 8px;
  overflow: hidden;
  background: #1a1a2e;
}

.movie-poster img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.no-poster {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #666;
  font-size: 2rem;
}

.movie-info {
  padding: 0.5rem 0;
}

.movie-title {
  font-size: 0.9rem;
  color: #fff;
}

.movie-year {
  font-size: 0.8rem;
  color: #999;
}

.loading, .error {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 50vh;
  color: #666;
}

@media (max-width: 768px) {
  .collection-header {
    flex-direction: column;
    align-items: center;
    text-align: center;
  }
}
</style>
```

**Step 2: Add route**

Add to `frontend/src/router/index.js`:

```javascript
// Add import
import CollectionView from '@/views/CollectionView.vue'

// Add route
{
  path: '/collection/:id',
  name: 'Collection',
  component: CollectionView
}
```

**Step 3: Commit**

```bash
git add frontend/src/views/CollectionView.vue
git add frontend/src/router/index.js
git commit -m "feat(media): add CollectionView for movie franchises"
```

---

## Task 12: Update MediaCard to Link to Detail

**Files:**
- Modify: `frontend/src/components/MediaCard.vue`

**Step 1: Update MediaCard**

Wrap MediaCard content in router-link:

```vue
<template>
  <router-link
    :to="`/${mediaType === 'movie' ? 'movie' : 'tv'}/${media.id}`"
    class="media-card"
  >
    <!-- existing content -->
  </router-link>
</template>
```

**Step 2: Commit**

```bash
git add frontend/src/components/MediaCard.vue
git commit -m "feat(media): link MediaCard to detail view"
```

---

## Task 13: Final Testing

**Step 1: Run backend tests**

```bash
cd backend && pytest -v
```

**Step 2: Manual testing**

1. Start servers
2. Click a movie poster → MediaDetailView
3. Click "Watch Trailer" → TrailerModal
4. Click actor → PersonView
5. Click collection link → CollectionView
6. Check "More Like This" carousel

**Step 3: Final commit**

```bash
git add -A
git commit -m "feat(media): complete media deep dive feature"
```

---

## Summary

| Task | Description |
|------|-------------|
| 1 | Person endpoint |
| 2 | Movie detail endpoint |
| 3 | Show detail endpoint |
| 4 | Collection endpoint |
| 5 | Frontend service updates |
| 6 | TrailerModal component |
| 7 | CastCarousel component |
| 8 | MediaCarousel component |
| 9 | MediaDetailView |
| 10 | PersonView |
| 11 | CollectionView |
| 12 | MediaCard linking |
| 13 | Testing |
