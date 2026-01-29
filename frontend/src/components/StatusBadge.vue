<template>
  <span :class="['badge', badgeClass]">
    {{ label }}
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: { type: String, default: null },
  mediaType: { type: String, default: 'movie' }
})

const isInLibrary = computed(() => props.status === 'available' || props.status === 'added')

const serviceName = computed(() => props.mediaType === 'movie' ? 'Radarr' : 'Sonarr')

const label = computed(() => {
  switch (props.status) {
    case 'available': return serviceName.value
    case 'downloading': return 'Downloading'
    case 'added': return serviceName.value
    case 'watchlist': return 'In Watchlist'
    default: return 'Add'
  }
})

const badgeClass = computed(() => {
  if (props.status === 'available') return 'in-library'
  if (props.status === 'added') return 'added'
  if (props.status === 'downloading') return 'downloading'
  if (props.status === 'watchlist') return 'watchlist'
  return 'add'
})
</script>

<style scoped>
.badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}
.in-library {
  background: #22c55e;
  color: white;
}
.downloading {
  background: #eab308;
  color: black;
}
.added {
  background: #3b82f6;
  color: white;
}
.watchlist {
  background: #8b5cf6;
  color: white;
}
.add {
  background: #e50914;
  color: white;
  cursor: pointer;
}
</style>
