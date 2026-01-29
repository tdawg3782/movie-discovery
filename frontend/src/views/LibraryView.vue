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
import { libraryService } from '@/services/library'
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
