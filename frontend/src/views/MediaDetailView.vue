<template>
  <div class="media-detail-view" v-if="media">
    <!-- Backdrop -->
    <div
      class="backdrop"
      :style="backdropStyle"
    ></div>

    <!-- Content -->
    <div class="content">
      <!-- Poster & Info -->
      <div class="main-info">
        <div class="poster">
          <img
            v-if="media.poster_path"
            :src="`https://image.tmdb.org/t/p/w342${media.poster_path}`"
            :alt="title"
          />
        </div>

        <div class="info">
          <h1>{{ title }}</h1>

          <div class="meta">
            <span v-if="releaseYear">{{ releaseYear }}</span>
            <span v-if="runtime">{{ runtime }}</span>
            <span v-if="rating" class="rating">&#x2605; {{ rating }}</span>
          </div>

          <div v-if="genres.length" class="genres">
            <span v-for="genre in genres" :key="genre.id" class="genre-tag">
              {{ genre.name }}
            </span>
          </div>

          <p class="overview">{{ media.overview }}</p>

          <!-- Collection Link -->
          <router-link
            v-if="media.belongs_to_collection"
            :to="`/collection/${media.belongs_to_collection.id}`"
            class="collection-link"
          >
            Part of {{ media.belongs_to_collection.name }}
          </router-link>

          <!-- Actions -->
          <div class="actions">
            <button
              v-if="hasTrailer"
              class="btn-trailer"
              @click="showTrailer = true"
            >
              &#x25B6; Watch Trailer
            </button>
            <button
              class="btn-add"
              :class="{ added: addedToWatchlist }"
              :disabled="addingToWatchlist || addedToWatchlist"
              @click="addToWatchlist"
            >
              {{ addedToWatchlist ? '✓ Added' : addingToWatchlist ? 'Adding...' : '+ Add to Watchlist' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Cast -->
      <CastCarousel
        v-if="cast.length"
        title="Cast"
        :cast="cast"
      />

      <!-- Recommendations -->
      <MediaCarousel
        v-if="recommendations.length"
        title="More Like This"
        :items="recommendations"
        :media-type="mediaType"
      />
    </div>

    <!-- Trailer Modal -->
    <TrailerModal
      :is-open="showTrailer"
      :videos="media.videos?.results || []"
      @close="showTrailer = false"
    />

    <!-- Season Select Modal (TV shows only) -->
    <SeasonSelectModal
      :is-open="showSeasonModal"
      :show="media"
      @close="showSeasonModal = false"
      @add="handleAddWithSeasons"
    />
  </div>

  <div v-else-if="loading" class="loading">
    Loading...
  </div>

  <div v-else class="error">
    Media not found
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import discoverService from '@/services/discover'
import { watchlistService } from '@/services/watchlist'
import CastCarousel from '@/components/CastCarousel.vue'
import MediaCarousel from '@/components/MediaCarousel.vue'
import TrailerModal from '@/components/TrailerModal.vue'
import SeasonSelectModal from '@/components/SeasonSelectModal.vue'

const route = useRoute()
const media = ref(null)
const loading = ref(true)
const showTrailer = ref(false)
const showSeasonModal = ref(false)
const addingToWatchlist = ref(false)
const addedToWatchlist = ref(false)

const mediaType = computed(() => route.meta.mediaType || 'movie')
const mediaId = computed(() => route.params.id)

const title = computed(() => media.value?.title || media.value?.name || '')
const releaseYear = computed(() => {
  const date = media.value?.release_date || media.value?.first_air_date
  return date ? new Date(date).getFullYear() : null
})
const runtime = computed(() => {
  if (media.value?.runtime) {
    const hours = Math.floor(media.value.runtime / 60)
    const mins = media.value.runtime % 60
    return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`
  }
  return null
})
const rating = computed(() => {
  return media.value?.vote_average
    ? media.value.vote_average.toFixed(1)
    : null
})
const genres = computed(() => media.value?.genres || [])
const cast = computed(() => media.value?.credits?.cast?.slice(0, 20) || [])
const recommendations = computed(() =>
  media.value?.recommendations?.results?.slice(0, 10) || []
)
const hasTrailer = computed(() =>
  media.value?.videos?.results?.some(
    v => v.site === 'YouTube' && (v.type === 'Trailer' || v.type === 'Teaser')
  )
)
const backdropStyle = computed(() => ({
  backgroundImage: media.value?.backdrop_path
    ? `url(https://image.tmdb.org/t/p/w1280${media.value.backdrop_path})`
    : 'none'
}))

onMounted(async () => {
  await fetchMedia()
})

watch(() => route.params.id, async () => {
  addedToWatchlist.value = false
  await fetchMedia()
})

async function fetchMedia() {
  loading.value = true
  media.value = null

  try {
    if (mediaType.value === 'movie') {
      media.value = await discoverService.getMovieDetail(mediaId.value)
    } else {
      media.value = await discoverService.getShowDetail(mediaId.value)
    }
  } catch (error) {
    console.error('Failed to fetch media:', error)
  } finally {
    loading.value = false
  }
}

async function addToWatchlist() {
  if (addingToWatchlist.value || addedToWatchlist.value) return

  // For TV shows, open season selector modal
  if (mediaType.value === 'tv') {
    showSeasonModal.value = true
    return
  }

  // For movies, add directly
  addingToWatchlist.value = true
  try {
    await watchlistService.add(mediaId.value, 'movie')
    addedToWatchlist.value = true
  } catch (error) {
    console.error('Failed to add to watchlist:', error)
  } finally {
    addingToWatchlist.value = false
  }
}

async function handleAddWithSeasons(selectedSeasons) {
  addingToWatchlist.value = true
  try {
    await watchlistService.add(mediaId.value, 'show', null, selectedSeasons)
    addedToWatchlist.value = true
    showSeasonModal.value = false
  } catch (error) {
    console.error('Failed to add to watchlist:', error)
  } finally {
    addingToWatchlist.value = false
  }
}
</script>

<style scoped>
.media-detail-view {
  position: relative;
  min-height: 100vh;
}

.backdrop {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 500px;
  background-size: cover;
  background-position: center top;
  opacity: 0.3;
  mask-image: linear-gradient(to bottom, black, transparent);
  -webkit-mask-image: linear-gradient(to bottom, black, transparent);
}

.content {
  position: relative;
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

.main-info {
  display: flex;
  gap: 2rem;
  margin-bottom: 2rem;
}

.poster {
  flex: 0 0 auto;
}

.poster img {
  width: 250px;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
}

.info {
  flex: 1;
}

.info h1 {
  font-size: 2.5rem;
  margin: 0 0 1rem;
  color: #fff;
}

.meta {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
  color: #999;
}

.rating {
  color: #ffc107;
}

.genres {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.genre-tag {
  padding: 0.25rem 0.75rem;
  background: #252540;
  border-radius: 20px;
  font-size: 0.85rem;
  color: #ccc;
}

.overview {
  color: #ccc;
  line-height: 1.6;
  margin-bottom: 1rem;
}

.collection-link {
  display: inline-block;
  color: #e94560;
  margin-bottom: 1rem;
}

.collection-link:hover {
  text-decoration: underline;
}

.actions {
  display: flex;
  gap: 1rem;
  margin-top: 1.5rem;
}

.btn-trailer {
  padding: 0.75rem 1.5rem;
  background: #e94560;
  border: none;
  border-radius: 4px;
  color: #fff;
  font-size: 1rem;
  cursor: pointer;
}

.btn-trailer:hover {
  background: #d63850;
}

.btn-add {
  padding: 0.75rem 1.5rem;
  background: transparent;
  border: 1px solid #e94560;
  border-radius: 4px;
  color: #e94560;
  font-size: 1rem;
  cursor: pointer;
}

.btn-add:hover {
  background: rgba(233, 69, 96, 0.1);
}

.loading, .error {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 50vh;
  color: #666;
  font-size: 1.2rem;
}

@media (max-width: 768px) {
  .main-info {
    flex-direction: column;
    align-items: center;
    text-align: center;
  }

  .genres {
    justify-content: center;
  }

  .actions {
    justify-content: center;
  }
}
</style>
