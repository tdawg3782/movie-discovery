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
