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
