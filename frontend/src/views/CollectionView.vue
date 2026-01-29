<template>
  <div class="collection-view" v-if="collection">
    <!-- Backdrop -->
    <div
      class="backdrop"
      :style="backdropStyle"
    ></div>

    <div class="content">
      <div class="collection-header">
        <div class="poster">
          <img
            v-if="collection.poster_path"
            :src="`https://image.tmdb.org/t/p/w300${collection.poster_path}`"
            :alt="collection.name"
          />
        </div>

        <div class="info">
          <h1>{{ collection.name }}</h1>
          <p class="overview">{{ collection.overview }}</p>
          <p class="count">{{ collection.parts?.length || 0 }} movies</p>
        </div>
      </div>

      <div class="movies-grid">
        <router-link
          v-for="movie in sortedMovies"
          :key="movie.id"
          :to="`/movie/${movie.id}`"
          class="movie-card"
        >
          <div class="movie-poster">
            <img
              v-if="movie.poster_path"
              :src="`https://image.tmdb.org/t/p/w185${movie.poster_path}`"
              :alt="movie.title"
            />
            <div v-else class="no-poster">?</div>
          </div>
          <div class="movie-info">
            <div class="movie-title">{{ movie.title }}</div>
            <div class="movie-year">{{ getYear(movie) }}</div>
          </div>
        </router-link>
      </div>
    </div>
  </div>

  <div v-else-if="loading" class="loading">Loading...</div>
  <div v-else class="error">Collection not found</div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import discoverService from '@/services/discover'

const route = useRoute()
const collection = ref(null)
const loading = ref(true)

const collectionId = computed(() => route.params.id)

const backdropStyle = computed(() => ({
  backgroundImage: collection.value?.backdrop_path
    ? `url(https://image.tmdb.org/t/p/w1280${collection.value.backdrop_path})`
    : 'none'
}))

const sortedMovies = computed(() => {
  if (!collection.value?.parts) return []
  return [...collection.value.parts].sort((a, b) => {
    const dateA = a.release_date || '9999'
    const dateB = b.release_date || '9999'
    return dateA.localeCompare(dateB)
  })
})

onMounted(async () => {
  await fetchCollection()
})

watch(() => route.params.id, async () => {
  await fetchCollection()
})

async function fetchCollection() {
  loading.value = true
  collection.value = null

  try {
    collection.value = await discoverService.getCollection(collectionId.value)
  } catch (error) {
    console.error('Failed to fetch collection:', error)
  } finally {
    loading.value = false
  }
}

function getYear(movie) {
  return movie.release_date
    ? new Date(movie.release_date).getFullYear()
    : 'TBA'
}
</script>

<style scoped>
.collection-view {
  position: relative;
  min-height: 100vh;
}

.backdrop {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 400px;
  background-size: cover;
  background-position: center;
  opacity: 0.3;
  mask-image: linear-gradient(to bottom, black, transparent);
  -webkit-mask-image: linear-gradient(to bottom, black, transparent);
}

.content {
  position: relative;
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.collection-header {
  display: flex;
  gap: 2rem;
  margin-bottom: 3rem;
}

.poster img {
  width: 200px;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
}

.info h1 {
  margin: 0 0 1rem;
  color: #fff;
  font-size: 2rem;
}

.overview {
  color: #ccc;
  line-height: 1.6;
  margin-bottom: 1rem;
}

.count {
  color: #999;
}

.movies-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 1.5rem;
}

.movie-card {
  text-decoration: none;
  color: inherit;
}

.movie-card:hover .movie-title {
  color: #e94560;
}

.movie-poster {
  width: 100%;
  aspect-ratio: 2/3;
  border-radius: 8px;
  overflow: hidden;
  background: #1a1a2e;
}

.movie-poster img {
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
  color: #666;
  font-size: 2rem;
}

.movie-info {
  padding: 0.5rem 0;
}

.movie-title {
  font-size: 0.9rem;
  color: #fff;
}

.movie-year {
  font-size: 0.8rem;
  color: #999;
}

.loading, .error {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 50vh;
  color: #666;
}

@media (max-width: 768px) {
  .collection-header {
    flex-direction: column;
    align-items: center;
    text-align: center;
  }
}
</style>
