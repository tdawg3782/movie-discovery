<template>
  <div class="person-view" v-if="person">
    <div class="person-header">
      <div class="person-image">
        <img
          v-if="person.profile_path"
          :src="`https://image.tmdb.org/t/p/w300${person.profile_path}`"
          :alt="person.name"
        />
        <div v-else class="no-image">
          {{ person.name.charAt(0) }}
        </div>
      </div>

      <div class="person-info">
        <h1>{{ person.name }}</h1>
        <p v-if="person.birthday" class="meta">
          Born: {{ formatDate(person.birthday) }}
          <span v-if="person.place_of_birth"> in {{ person.place_of_birth }}</span>
        </p>
        <p v-if="person.biography" class="biography">
          {{ truncatedBio }}
          <button v-if="person.biography.length > 500" @click="showFullBio = !showFullBio">
            {{ showFullBio ? 'Show less' : 'Read more' }}
          </button>
        </p>
      </div>
    </div>

    <div class="filmography">
      <h2>Known For</h2>

      <div class="tabs">
        <button
          :class="['tab', { active: activeTab === 'movies' }]"
          @click="activeTab = 'movies'"
        >
          Movies ({{ movies.length }})
        </button>
        <button
          :class="['tab', { active: activeTab === 'tv' }]"
          @click="activeTab = 'tv'"
        >
          TV Shows ({{ tvShows.length }})
        </button>
      </div>

      <div class="credits-grid">
        <router-link
          v-for="item in activeCredits"
          :key="`${item.media_type}-${item.id}`"
          :to="`/${item.media_type === 'movie' ? 'movie' : 'tv'}/${item.id}`"
          class="credit-card"
        >
          <div class="credit-poster">
            <img
              v-if="item.poster_path"
              :src="`https://image.tmdb.org/t/p/w185${item.poster_path}`"
              :alt="item.title || item.name"
            />
            <div v-else class="no-poster">?</div>
          </div>
          <div class="credit-info">
            <div class="credit-title">{{ item.title || item.name }}</div>
            <div class="credit-role">{{ item.character || item.job }}</div>
            <div class="credit-year">{{ getYear(item) }}</div>
          </div>
        </router-link>
      </div>
    </div>
  </div>

  <div v-else-if="loading" class="loading">Loading...</div>
  <div v-else class="error">Person not found</div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import discoverService from '@/services/discover'

const route = useRoute()
const person = ref(null)
const loading = ref(true)
const showFullBio = ref(false)
const activeTab = ref('movies')

const personId = computed(() => route.params.id)

const truncatedBio = computed(() => {
  if (!person.value?.biography) return ''
  if (showFullBio.value || person.value.biography.length <= 500) {
    return person.value.biography
  }
  return person.value.biography.slice(0, 500) + '...'
})

const movies = computed(() => {
  const credits = person.value?.combined_credits?.cast || []
  return credits
    .filter(c => c.media_type === 'movie')
    .sort((a, b) => (b.popularity || 0) - (a.popularity || 0))
})

const tvShows = computed(() => {
  const credits = person.value?.combined_credits?.cast || []
  return credits
    .filter(c => c.media_type === 'tv')
    .sort((a, b) => (b.popularity || 0) - (a.popularity || 0))
})

const activeCredits = computed(() => {
  return activeTab.value === 'movies' ? movies.value : tvShows.value
})

onMounted(async () => {
  await fetchPerson()
})

watch(() => route.params.id, async () => {
  await fetchPerson()
})

async function fetchPerson() {
  loading.value = true
  person.value = null

  try {
    person.value = await discoverService.getPerson(personId.value)
  } catch (error) {
    console.error('Failed to fetch person:', error)
  } finally {
    loading.value = false
  }
}

function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

function getYear(item) {
  const date = item.release_date || item.first_air_date
  return date ? new Date(date).getFullYear() : ''
}
</script>

<style scoped>
.person-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.person-header {
  display: flex;
  gap: 2rem;
  margin-bottom: 3rem;
}

.person-image {
  flex: 0 0 auto;
}

.person-image img {
  width: 200px;
  border-radius: 8px;
}

.no-image {
  width: 200px;
  height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #252540;
  border-radius: 8px;
  color: #666;
  font-size: 4rem;
}

.person-info h1 {
  margin: 0 0 0.5rem;
  color: #fff;
}

.meta {
  color: #999;
  margin-bottom: 1rem;
}

.biography {
  color: #ccc;
  line-height: 1.6;
}

.biography button {
  background: none;
  border: none;
  color: #e94560;
  cursor: pointer;
  padding: 0;
  margin-left: 0.5rem;
}

.biography button:hover {
  text-decoration: underline;
}

.filmography h2 {
  color: #fff;
  margin-bottom: 1rem;
}

.tabs {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.tab {
  padding: 0.5rem 1rem;
  background: transparent;
  border: 1px solid #333;
  border-radius: 4px;
  color: #ccc;
  cursor: pointer;
}

.tab:hover {
  border-color: #555;
}

.tab.active {
  background: #e94560;
  border-color: #e94560;
  color: #fff;
}

.credits-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 1.5rem;
}

.credit-card {
  text-decoration: none;
  color: inherit;
}

.credit-card:hover .credit-title {
  color: #e94560;
}

.credit-poster {
  width: 100%;
  aspect-ratio: 2/3;
  border-radius: 8px;
  overflow: hidden;
  background: #1a1a2e;
}

.credit-poster img {
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

.credit-info {
  padding: 0.5rem 0;
}

.credit-title {
  font-size: 0.9rem;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.credit-role {
  font-size: 0.8rem;
  color: #999;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.credit-year {
  font-size: 0.8rem;
  color: #666;
}

.loading, .error {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 50vh;
  color: #666;
}

@media (max-width: 768px) {
  .person-header {
    flex-direction: column;
    align-items: center;
    text-align: center;
  }
}
</style>
