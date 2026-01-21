<template>
  <div class="watchlist-view">
    <h2>My Watchlist</h2>

    <div v-if="loading" class="loading">Loading watchlist...</div>

    <div v-else-if="error" class="error">
      <p>{{ error }}</p>
      <button @click="fetchWatchlist">Retry</button>
    </div>

    <div v-else-if="items.length === 0" class="empty">
      <p>Your watchlist is empty.</p>
      <router-link to="/" class="discover-link">Discover movies and shows</router-link>
    </div>

    <div v-else class="watchlist-grid">
      <div v-for="item in items" :key="item.id" class="watchlist-item">
        <MediaCard :media="formatForCard(item)" />
        <button class="remove-btn" @click="handleRemove(item.id)" :disabled="removing === item.id">
          {{ removing === item.id ? 'Removing...' : 'Remove' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import MediaCard from '../components/MediaCard.vue'
import { watchlistService } from '../services/watchlist'

const items = ref([])
const loading = ref(false)
const error = ref(null)
const removing = ref(null)

const fetchWatchlist = async () => {
  loading.value = true
  error.value = null

  try {
    const response = await watchlistService.getAll()
    items.value = response.data || []
  } catch (err) {
    error.value = err.response?.data?.detail || 'Failed to load watchlist'
    items.value = []
  } finally {
    loading.value = false
  }
}

const formatForCard = (item) => {
  // Transform watchlist item to MediaCard expected format
  return {
    id: item.tmdb_id,
    title: item.title || item.name || 'Unknown Title',
    poster_path: item.poster_path,
    release_date: item.release_date || item.first_air_date,
    vote_average: item.vote_average,
    library_status: item.library_status
  }
}

const handleRemove = async (id) => {
  removing.value = id

  try {
    await watchlistService.remove(id)
    items.value = items.value.filter(item => item.id !== id)
  } catch (err) {
    console.error('Failed to remove from watchlist:', err)
    alert(err.response?.data?.detail || 'Failed to remove from watchlist')
  } finally {
    removing.value = null
  }
}

onMounted(() => {
  fetchWatchlist()
})
</script>

<style scoped>
.watchlist-view {
  padding: 20px 0;
}

.watchlist-view h2 {
  margin-bottom: 24px;
  font-size: 24px;
}

.watchlist-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 20px;
}

.watchlist-item {
  display: flex;
  flex-direction: column;
}

.remove-btn {
  margin-top: 8px;
  padding: 8px 12px;
  background: transparent;
  border: 1px solid #444;
  border-radius: 4px;
  color: #888;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.remove-btn:hover:not(:disabled) {
  background: #e50914;
  border-color: #e50914;
  color: white;
}

.remove-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
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

.error button,
.discover-link {
  display: inline-block;
  margin-top: 16px;
  padding: 8px 20px;
  background: #e50914;
  border: none;
  border-radius: 4px;
  color: white;
  text-decoration: none;
  cursor: pointer;
}

.error button:hover,
.discover-link:hover {
  background: #f40d17;
}
</style>
