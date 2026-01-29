<template>
  <div class="discover-view">
    <div class="search-bar">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Search movies and TV shows..."
        @keyup.enter="performSearch()"
      />
      <button v-if="searchQuery" class="clear-btn" @click="clearSearch">×</button>
    </div>

    <div v-if="!isSearching" class="tabs">
      <button
        :class="{ active: activeTab === 'movies' }"
        @click="activeTab = 'movies'"
      >
        Movies
      </button>
      <button
        :class="{ active: activeTab === 'shows' }"
        @click="activeTab = 'shows'"
      >
        Shows
      </button>
    </div>

    <div v-if="isSearching" class="search-header">
      <span>Search results for "{{ searchQuery }}"</span>
    </div>

    <div v-if="loading" class="loading">{{ isSearching ? 'Searching...' : `Loading trending ${activeTab}...` }}</div>

    <div v-else-if="error" class="error">
      <p>{{ error }}</p>
      <button @click="fetchTrending">Retry</button>
    </div>

    <div v-else-if="items.length === 0" class="empty">
      No trending {{ activeTab }} found.
    </div>

    <div v-else class="media-grid">
      <MediaCard
        v-for="item in items"
        :key="`${item.tmdb_id}-${item.media_type}`"
        :media="item"
        @add="handleAdd"
      />
    </div>

    <div v-if="!loading && items.length > 0 && currentPage < totalPages" class="load-more">
      <button @click="loadNextPage">Load More</button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import MediaCard from '../components/MediaCard.vue'
import { discoverService } from '../services/discover'
import { libraryService } from '../services/library'
import { watchlistService } from '../services/watchlist'

const activeTab = ref('movies')
const items = ref([])
const loading = ref(false)
const error = ref(null)
const searchQuery = ref('')
const isSearching = ref(false)
const currentPage = ref(1)
const totalPages = ref(1)

const fetchLibraryStatuses = async (mediaItems) => {
  if (!mediaItems.length) return

  try {
    // Separate movies and shows
    const movieIds = mediaItems.filter(m => m.media_type === 'movie').map(m => m.tmdb_id)
    const showIds = mediaItems.filter(m => m.media_type === 'show').map(m => m.tmdb_id)

    // Fetch statuses in parallel
    const [movieStatuses, showStatuses] = await Promise.all([
      movieIds.length ? libraryService.getBatchMovieStatus(movieIds) : Promise.resolve({ statuses: {} }),
      showIds.length ? libraryService.getBatchShowStatus(showIds) : Promise.resolve({ statuses: {} }),
    ])

    // Merge statuses into items
    items.value = items.value.map(item => {
      const statuses = item.media_type === 'movie' ? movieStatuses.statuses : showStatuses.statuses
      const status = statuses[item.tmdb_id]
      return status ? { ...item, library_status: status } : item
    })
  } catch (err) {
    // Don't fail the whole view if status check fails
    console.warn('Failed to fetch library statuses:', err)
  }
}

const fetchTrending = async () => {
  loading.value = true
  error.value = null
  isSearching.value = false
  currentPage.value = 1

  try {
    const response = activeTab.value === 'movies'
      ? await discoverService.getTrendingMovies()
      : await discoverService.getTrendingShows()

    items.value = response.results || []
    totalPages.value = response.total_pages || 1

    // Fetch library statuses for the loaded items
    await fetchLibraryStatuses(items.value)
  } catch (err) {
    error.value = err.response?.data?.detail || 'Failed to load trending content'
    items.value = []
  } finally {
    loading.value = false
  }
}

const performSearch = async (page = 1, append = false) => {
  if (!searchQuery.value.trim()) {
    clearSearch()
    return
  }

  loading.value = true
  error.value = null
  isSearching.value = true
  currentPage.value = page

  try {
    const response = await discoverService.search(searchQuery.value, page)
    const newResults = response.results || []
    items.value = append ? [...items.value, ...newResults] : newResults
    totalPages.value = response.total_pages || 1

    // Fetch library statuses for search results
    await fetchLibraryStatuses(append ? newResults : items.value)
  } catch (err) {
    error.value = err.response?.data?.detail || 'Search failed'
    if (!append) items.value = []
  } finally {
    loading.value = false
  }
}

const clearSearch = () => {
  searchQuery.value = ''
  isSearching.value = false
  currentPage.value = 1
  fetchTrending()
}

const loadNextPage = () => {
  if (currentPage.value < totalPages.value) {
    if (isSearching.value) {
      performSearch(currentPage.value + 1, true)
    } else {
      fetchTrendingPage(currentPage.value + 1)
    }
  }
}

const fetchTrendingPage = async (page) => {
  loading.value = true
  currentPage.value = page

  try {
    const response = activeTab.value === 'movies'
      ? await discoverService.getTrendingMovies(page)
      : await discoverService.getTrendingShows(page)

    const newResults = response.results || []
    items.value = [...items.value, ...newResults]
    totalPages.value = response.total_pages || 1

    // Fetch library statuses for new items
    await fetchLibraryStatuses(newResults)
  } catch (err) {
    error.value = 'Failed to load more content'
  } finally {
    loading.value = false
  }
}

const handleAdd = async (media) => {
  try {
    // Add to watchlist instead of directly to Radarr/Sonarr
    const mediaType = media.media_type || (activeTab.value === 'movies' ? 'movie' : 'show')
    await watchlistService.add(media.tmdb_id, mediaType)

    // Update local state to show item is in watchlist
    const index = items.value.findIndex(item => item.tmdb_id === media.tmdb_id && item.media_type === media.media_type)
    if (index !== -1) {
      items.value[index] = { ...items.value[index], library_status: 'watchlist' }
    }
  } catch (err) {
    console.error('Failed to add to watchlist:', err)
    alert(err.response?.data?.detail || 'Failed to add to watchlist')
  }
}

watch(activeTab, () => {
  fetchTrending()
})

onMounted(() => {
  fetchTrending()
})
</script>

<style scoped>
.discover-view {
  padding: 20px 0;
}

.tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 24px;
}

.tabs button {
  padding: 10px 24px;
  background: #2a2a2a;
  border: none;
  border-radius: 6px;
  color: #e0e0e0;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.tabs button:hover {
  background: #3a3a3a;
}

.tabs button.active {
  background: #e50914;
  color: white;
}

.media-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 20px;
}

.loading,
.error,
.empty {
  text-align: center;
  padding: 60px 20px;
  color: #888;
}

.error {
  color: #e50914;
}

.error button {
  margin-top: 16px;
  padding: 8px 20px;
  background: #e50914;
  border: none;
  border-radius: 4px;
  color: white;
  cursor: pointer;
}

.error button:hover {
  background: #f40d17;
}

.search-bar {
  position: relative;
  margin-bottom: 20px;
}

.search-bar input {
  width: 100%;
  padding: 14px 40px 14px 16px;
  background: #2a2a2a;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  color: #e0e0e0;
  font-size: 16px;
  outline: none;
  transition: border-color 0.2s;
}

.search-bar input:focus {
  border-color: #e50914;
}

.search-bar input::placeholder {
  color: #666;
}

.search-bar .clear-btn {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: #888;
  font-size: 20px;
  cursor: pointer;
  padding: 4px 8px;
}

.search-bar .clear-btn:hover {
  color: #e50914;
}

.search-header {
  margin-bottom: 20px;
  color: #888;
  font-size: 14px;
}

.load-more {
  text-align: center;
  padding: 30px 0;
}

.load-more button {
  padding: 12px 40px;
  background: #2a2a2a;
  border: 1px solid #3a3a3a;
  border-radius: 6px;
  color: #e0e0e0;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.load-more button:hover {
  background: #3a3a3a;
  border-color: #e50914;
}
</style>
