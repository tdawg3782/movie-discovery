<template>
  <div class="discover-view">
    <div class="tabs">
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

    <div v-if="loading" class="loading">Loading trending {{ activeTab }}...</div>

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
        :key="item.id"
        :media="item"
        @add="handleAdd"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import MediaCard from '../components/MediaCard.vue'
import { discoverService } from '../services/discover'
import { libraryService } from '../services/library'

const activeTab = ref('movies')
const items = ref([])
const loading = ref(false)
const error = ref(null)

const fetchTrending = async () => {
  loading.value = true
  error.value = null

  try {
    const response = activeTab.value === 'movies'
      ? await discoverService.getTrendingMovies()
      : await discoverService.getTrendingShows()

    items.value = response.data.results || response.data || []
  } catch (err) {
    error.value = err.response?.data?.detail || 'Failed to load trending content'
    items.value = []
  } finally {
    loading.value = false
  }
}

const handleAdd = async (media) => {
  try {
    if (activeTab.value === 'movies') {
      await libraryService.addMovie(media.id)
    } else {
      await libraryService.addShow(media.id)
    }
    // Update local state to reflect the change
    const index = items.value.findIndex(item => item.id === media.id)
    if (index !== -1) {
      items.value[index] = { ...items.value[index], library_status: 'added' }
    }
  } catch (err) {
    console.error('Failed to add to library:', err)
    alert(err.response?.data?.detail || 'Failed to add to library')
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
</style>
