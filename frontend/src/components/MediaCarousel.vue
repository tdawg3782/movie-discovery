<template>
  <div class="media-carousel">
    <h3>{{ title }}</h3>
    <div class="carousel-container">
      <div class="carousel-scroll">
        <router-link
          v-for="item in items"
          :key="item.id"
          :to="`/${mediaType === 'movie' ? 'movie' : 'tv'}/${item.id}`"
          class="media-card-small"
        >
          <div class="poster">
            <img
              v-if="item.poster_path"
              :src="`https://image.tmdb.org/t/p/w185${item.poster_path}`"
              :alt="item.title || item.name"
            />
            <div v-else class="no-poster">
              {{ (item.title || item.name || '?').charAt(0) }}
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
