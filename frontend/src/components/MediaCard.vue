<template>
  <router-link :to="detailLink" class="media-card">
    <div class="poster">
      <img
        v-if="media.poster_path"
        :src="`https://image.tmdb.org/t/p/w300${media.poster_path}`"
        :alt="media.title"
      />
      <div v-else class="no-poster">No Image</div>
      <StatusBadge
        :status="media.library_status"
        :media-type="media.media_type"
        class="status-overlay"
        @click.prevent="handleAdd"
      />
    </div>
    <div class="info">
      <h3>{{ media.title }}</h3>
      <p class="meta">
        {{ media.release_date?.slice(0, 4) }}
        <span v-if="media.vote_average">• {{ media.vote_average.toFixed(1) }}</span>
      </p>
    </div>
  </router-link>
</template>

<script setup>
import { computed } from 'vue'
import StatusBadge from './StatusBadge.vue'

const props = defineProps({
  media: { type: Object, required: true }
})

const emit = defineEmits(['add'])

const detailLink = computed(() => {
  const type = props.media.media_type === 'movie' ? 'movie' : 'tv'
  return `/${type}/${props.media.tmdb_id}`
})

const handleAdd = () => {
  if (!props.media.library_status) {
    emit('add', props.media)
  }
}
</script>

<style scoped>
.media-card {
  display: block;
  text-decoration: none;
  color: inherit;
  background: #1a1a1a;
  border-radius: 8px;
  overflow: hidden;
  transition: transform 0.2s;
}
.media-card:hover {
  transform: scale(1.02);
}
.poster {
  position: relative;
  aspect-ratio: 2/3;
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
  background: #333;
  color: #666;
}
.status-overlay {
  position: absolute;
  bottom: 8px;
  right: 8px;
}
.info {
  padding: 12px;
}
.info h3 {
  font-size: 14px;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.meta {
  font-size: 12px;
  color: #888;
}
</style>
