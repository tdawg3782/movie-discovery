<template>
  <div class="for-you-view">
    <h1>For You</h1>

    <div v-if="loading" class="loading">Loading...</div>

    <div v-else-if="error" class="error">
      <p>{{ error }}</p>
      <button @click="load">Retry</button>
    </div>

    <div v-else-if="items.length === 0" class="empty">
      Add movies and shows to your watchlist or library to start getting recommendations.
    </div>

    <div v-else class="media-grid">
      <MediaCard
        v-for="item in items"
        :key="`${item.tmdb_id}-${item.media_type}`"
        :media="item"
        @add="handleAdd"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import MediaCard from '../components/MediaCard.vue'
import { forYouService } from '@/services/forYou'
import { watchlistService } from '@/services/watchlist'
import { addTargetFor } from '@/utils/forYouState'

const loading = ref(true)
const error = ref(null)
const items = ref([])

const router = useRouter()

async function load() {
  loading.value = true
  error.value = null
  try {
    const data = await forYouService.getRecommendations()
    items.value = data.results || []
  } catch (e) {
    error.value = 'Failed to load recommendations'
    console.error('Failed to load recommendations:', e)
  } finally {
    loading.value = false
  }
}

onMounted(load)

async function handleAdd(media) {
  const target = addTargetFor(media)
  if (target.kind === 'watchlist') {
    try {
      await watchlistService.add(media.tmdb_id, 'movie')
      const i = items.value.findIndex(m => m.tmdb_id === media.tmdb_id && m.media_type === media.media_type)
      if (i !== -1) items.value[i] = { ...items.value[i], library_status: 'watchlist' }
    } catch (e) {
      console.error('Failed to add to watchlist:', e)
      alert(e.response?.data?.detail || 'Failed to add to watchlist')
    }
  } else {
    router.push(target.path)
  }
}
</script>

<style scoped>
.for-you-view h1 {
  margin-bottom: 20px;
}

.media-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 20px;
}

.loading,
.empty,
.error {
  padding: 40px;
  text-align: center;
  color: #888;
}
</style>
