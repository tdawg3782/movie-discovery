<template>
  <div class="filter-panel" :class="{ open: isOpen }">
    <button class="filter-toggle" @click="isOpen = !isOpen">
      <span>Filters</span>
      <span class="toggle-icon">{{ isOpen ? '▼' : '▶' }}</span>
    </button>

    <div v-if="isOpen" class="filter-content">
      <!-- Genre Filter -->
      <div class="filter-group">
        <label>Genre</label>
        <div class="genre-chips">
          <button
            v-for="genre in genres"
            :key="genre.id"
            :class="['chip', { active: selectedGenres.includes(genre.id) }]"
            @click="toggleGenre(genre.id)"
          >
            {{ genre.name }}
          </button>
        </div>
      </div>

      <!-- Year Filter -->
      <div class="filter-group">
        <label>Year Range</label>
        <div class="range-inputs">
          <input
            type="number"
            v-model.number="filters.yearGte"
            :min="1900"
            :max="currentYear + 1"
            placeholder="From"
          />
          <span>to</span>
          <input
            type="number"
            v-model.number="filters.yearLte"
            :min="1900"
            :max="currentYear + 1"
            placeholder="To"
          />
        </div>
      </div>

      <!-- Rating Filter -->
      <div class="filter-group">
        <label>Minimum Rating: {{ filters.ratingGte || 'Any' }}</label>
        <input
          type="range"
          v-model.number="filters.ratingGte"
          min="0"
          max="10"
          step="0.5"
        />
      </div>

      <!-- Content Rating Filter (Movies only) -->
      <div v-if="mediaType === 'movie'" class="filter-group">
        <label>Content Rating</label>
        <select v-model="filters.certification">
          <option value="">Any</option>
          <option value="G">G</option>
          <option value="PG">PG</option>
          <option value="PG-13">PG-13</option>
          <option value="R">R</option>
        </select>
      </div>

      <!-- Sort By -->
      <div class="filter-group">
        <label>Sort By</label>
        <select v-model="filters.sortBy">
          <option value="popularity.desc">Most Popular</option>
          <option value="vote_average.desc">Highest Rated</option>
          <option value="primary_release_date.desc">Newest</option>
          <option value="primary_release_date.asc">Oldest</option>
        </select>
      </div>

      <!-- Library Status Filter -->
      <div class="filter-group">
        <label>Library Status</label>
        <div class="checkbox-group">
          <label class="checkbox-item">
            <input
              type="checkbox"
              v-model="filters.inLibrary"
            />
            <span>{{ mediaType === 'movie' ? 'In Radarr' : 'In Sonarr' }}</span>
          </label>
          <label class="checkbox-item">
            <input
              type="checkbox"
              v-model="filters.notInLibrary"
            />
            <span>Not in Library</span>
          </label>
        </div>
      </div>

      <!-- Actions -->
      <div class="filter-actions">
        <button class="btn-apply" @click="applyFilters">Apply Filters</button>
        <button class="btn-clear" @click="clearFilters">Clear All</button>
      </div>

      <!-- Active Filters Display -->
      <div v-if="hasActiveFilters" class="active-filters">
        <span
          v-for="filter in activeFilterChips"
          :key="filter.key"
          class="active-chip"
          @click="removeFilter(filter.key)"
        >
          {{ filter.label }} ✕
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { discoverService } from '@/services/discover'

const props = defineProps({
  mediaType: {
    type: String,
    default: 'movie'
  }
})

const emit = defineEmits(['filter-change'])

const isOpen = ref(false)
const genres = ref([])
const selectedGenres = ref([])
const currentYear = new Date().getFullYear()

const filters = reactive({
  yearGte: null,
  yearLte: null,
  ratingGte: null,
  certification: '',
  sortBy: 'popularity.desc',
  inLibrary: false,
  notInLibrary: false
})

onMounted(async () => {
  await loadGenres()
})

watch(() => props.mediaType, async () => {
  await loadGenres()
  selectedGenres.value = []
})

async function loadGenres() {
  try {
    if (props.mediaType === 'movie') {
      genres.value = await discoverService.getMovieGenres()
    } else {
      genres.value = await discoverService.getTvGenres()
    }
  } catch (error) {
    console.error('Failed to load genres:', error)
  }
}

function toggleGenre(genreId) {
  const index = selectedGenres.value.indexOf(genreId)
  if (index === -1) {
    selectedGenres.value.push(genreId)
  } else {
    selectedGenres.value.splice(index, 1)
  }
}

const hasActiveFilters = computed(() => {
  return (
    selectedGenres.value.length > 0 ||
    filters.yearGte ||
    filters.yearLte ||
    filters.ratingGte ||
    filters.certification ||
    filters.sortBy !== 'popularity.desc' ||
    filters.inLibrary ||
    filters.notInLibrary
  )
})

const activeFilterChips = computed(() => {
  const chips = []

  if (selectedGenres.value.length > 0) {
    const genreNames = selectedGenres.value
      .map(id => genres.value.find(g => g.id === id)?.name)
      .filter(Boolean)
      .join(', ')
    chips.push({ key: 'genre', label: `Genre: ${genreNames}` })
  }

  if (filters.yearGte || filters.yearLte) {
    const yearLabel = filters.yearGte && filters.yearLte
      ? `${filters.yearGte}-${filters.yearLte}`
      : filters.yearGte
        ? `After ${filters.yearGte}`
        : `Before ${filters.yearLte}`
    chips.push({ key: 'year', label: `Year: ${yearLabel}` })
  }

  if (filters.ratingGte) {
    chips.push({ key: 'rating', label: `Rating: ${filters.ratingGte}+` })
  }

  if (filters.certification) {
    chips.push({ key: 'certification', label: `Rated: ${filters.certification}` })
  }

  if (filters.sortBy !== 'popularity.desc') {
    const sortLabels = {
      'vote_average.desc': 'Highest Rated',
      'primary_release_date.desc': 'Newest',
      'primary_release_date.asc': 'Oldest'
    }
    chips.push({ key: 'sort', label: `Sort: ${sortLabels[filters.sortBy]}` })
  }

  if (filters.inLibrary || filters.notInLibrary) {
    const labels = []
    if (filters.inLibrary) labels.push(props.mediaType === 'movie' ? 'In Radarr' : 'In Sonarr')
    if (filters.notInLibrary) labels.push('Not in Library')
    chips.push({ key: 'library', label: `Library: ${labels.join(', ')}` })
  }

  return chips
})

function removeFilter(key) {
  if (key === 'genre') {
    selectedGenres.value = []
  } else if (key === 'year') {
    filters.yearGte = null
    filters.yearLte = null
  } else if (key === 'rating') {
    filters.ratingGte = null
  } else if (key === 'certification') {
    filters.certification = ''
  } else if (key === 'sort') {
    filters.sortBy = 'popularity.desc'
  } else if (key === 'library') {
    filters.inLibrary = false
    filters.notInLibrary = false
  }
  applyFilters()
}

function applyFilters() {
  emit('filter-change', {
    genre: selectedGenres.value.join(',') || null,
    yearGte: filters.yearGte,
    yearLte: filters.yearLte,
    ratingGte: filters.ratingGte,
    certification: filters.certification || null,
    sortBy: filters.sortBy,
    inLibrary: filters.inLibrary,
    notInLibrary: filters.notInLibrary
  })
}

function clearFilters() {
  selectedGenres.value = []
  filters.yearGte = null
  filters.yearLte = null
  filters.ratingGte = null
  filters.certification = ''
  filters.sortBy = 'popularity.desc'
  filters.inLibrary = false
  filters.notInLibrary = false
  applyFilters()
}
</script>

<style scoped>
.filter-panel {
  background: #1a1a1a;
  border-radius: 8px;
  margin-bottom: 1rem;
}

.filter-toggle {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: none;
  border: none;
  color: #fff;
  font-size: 1rem;
  cursor: pointer;
}

.filter-content {
  padding: 0 1rem 1rem;
}

.filter-group {
  margin-bottom: 1rem;
}

.filter-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: #ccc;
  font-size: 0.9rem;
}

.genre-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.chip {
  padding: 0.5rem 1rem;
  border: 1px solid #333;
  border-radius: 20px;
  background: transparent;
  color: #ccc;
  cursor: pointer;
  font-size: 0.85rem;
}

.chip.active {
  background: #e94560;
  border-color: #e94560;
  color: #fff;
}

.chip:hover:not(.active) {
  border-color: #e94560;
}

.range-inputs {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.range-inputs input {
  width: 100px;
  padding: 0.5rem;
  border: 1px solid #333;
  border-radius: 4px;
  background: #0f0f0f;
  color: #fff;
}

.range-inputs span {
  color: #ccc;
}

input[type="range"] {
  width: 100%;
  accent-color: #e94560;
}

select {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #333;
  border-radius: 4px;
  background: #0f0f0f;
  color: #fff;
}

.filter-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
}

.btn-apply {
  flex: 1;
  padding: 0.75rem;
  border: none;
  border-radius: 4px;
  background: #e94560;
  color: #fff;
  cursor: pointer;
}

.btn-clear {
  padding: 0.75rem 1rem;
  border: 1px solid #333;
  border-radius: 4px;
  background: transparent;
  color: #ccc;
  cursor: pointer;
}

.active-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #333;
}

.active-chip {
  padding: 0.25rem 0.75rem;
  background: #252525;
  border-radius: 20px;
  color: #fff;
  font-size: 0.8rem;
  cursor: pointer;
}

.active-chip:hover {
  background: #e94560;
}

.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.checkbox-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #ccc;
  cursor: pointer;
}

.checkbox-item input {
  width: 16px;
  height: 16px;
  cursor: pointer;
}
</style>
