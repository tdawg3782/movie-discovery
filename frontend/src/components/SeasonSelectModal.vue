<template>
  <div v-if="isOpen" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal">
      <div class="modal-header">
        <h2>{{ isUpdate ? 'Add More Seasons' : 'Add to Watchlist' }}</h2>
        <button class="close-btn" @click="$emit('close')">&times;</button>
      </div>

      <div class="modal-body">
        <div class="show-info">
          <img
            v-if="show.poster_path"
            :src="`https://image.tmdb.org/t/p/w92${show.poster_path}`"
            :alt="show.name"
            class="poster"
          />
          <div>
            <h3>{{ show.name || show.title }}</h3>
            <p class="year">{{ releaseYear }}</p>
          </div>
        </div>

        <div v-if="loading" class="loading">Loading seasons...</div>

        <div v-else class="seasons-list">
          <label v-if="availableSeasons.length > 0" class="season-item select-all">
            <input
              type="checkbox"
              :checked="allSelected"
              :indeterminate.prop="someSelected && !allSelected"
              @change="toggleAll"
            />
            <span>Select All Available</span>
          </label>

          <div
            v-for="season in displaySeasons"
            :key="season.number"
            :class="['season-item', season.status]"
          >
            <input
              v-if="season.status === 'available'"
              type="checkbox"
              :checked="isSelected(season.number)"
              @change="toggleSeason(season.number)"
            />
            <span class="status-indicator" :class="season.status"></span>
            <span>Season {{ season.number }}</span>
            <span class="episode-count">
              <template v-if="season.episodes">({{ season.episodes }})</template>
              <template v-else>({{ season.episode_count }} episodes)</template>
            </span>
          </div>

          <div v-if="availableSeasons.length === 0 && isUpdate" class="no-seasons">
            All seasons are already monitored or downloaded.
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn-cancel" @click="$emit('close')">Cancel</button>
        <button
          class="btn-add"
          @click="handleAdd"
          :disabled="selectedSeasons.length === 0 || adding"
        >
          {{ adding ? 'Adding...' : buttonText }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  isOpen: { type: Boolean, default: false },
  show: { type: Object, required: true },
  existingSeasons: { type: Array, default: null } // From Sonarr if already in library
})

const emit = defineEmits(['close', 'add'])

const loading = ref(false)
const adding = ref(false)
const selectedSeasons = ref([])

// Check if this is an update (show already in Sonarr)
const isUpdate = computed(() => props.existingSeasons !== null)

// Combine TMDB seasons with Sonarr status
const displaySeasons = computed(() => {
  const tmdbSeasons = (props.show.seasons || []).filter(s => s.season_number > 0)

  if (!props.existingSeasons) {
    // New show - all seasons available
    return tmdbSeasons.map(s => ({
      number: s.season_number,
      status: 'available',
      episode_count: s.episode_count
    }))
  }

  // Existing show - merge with Sonarr status
  return tmdbSeasons.map(s => {
    const sonarrSeason = props.existingSeasons.find(es => es.number === s.season_number)
    return {
      number: s.season_number,
      status: sonarrSeason?.status || 'available',
      episodes: sonarrSeason?.episodes,
      episode_count: s.episode_count
    }
  })
})

const availableSeasons = computed(() =>
  displaySeasons.value.filter(s => s.status === 'available')
)

const releaseYear = computed(() => {
  const date = props.show.first_air_date
  return date ? new Date(date).getFullYear() : ''
})

const allSelected = computed(() =>
  availableSeasons.value.length > 0 &&
  availableSeasons.value.every(s => selectedSeasons.value.includes(s.number))
)

const someSelected = computed(() => selectedSeasons.value.length > 0)

const buttonText = computed(() => {
  const count = selectedSeasons.value.length
  if (isUpdate.value) {
    return count === 0 ? 'Select Seasons' : `Add ${count} Season${count > 1 ? 's' : ''}`
  }
  return 'Add to Watchlist'
})

// Initialize selection when modal opens
watch(() => props.isOpen, (open) => {
  if (open) {
    if (isUpdate.value) {
      // For updates, start with nothing selected
      selectedSeasons.value = []
    } else {
      // For new shows, select all
      selectedSeasons.value = availableSeasons.value.map(s => s.number)
    }
  }
})

function isSelected(seasonNumber) {
  return selectedSeasons.value.includes(seasonNumber)
}

function toggleSeason(seasonNumber) {
  const index = selectedSeasons.value.indexOf(seasonNumber)
  if (index === -1) {
    selectedSeasons.value.push(seasonNumber)
  } else {
    selectedSeasons.value.splice(index, 1)
  }
}

function toggleAll() {
  if (allSelected.value) {
    selectedSeasons.value = []
  } else {
    selectedSeasons.value = availableSeasons.value.map(s => s.number)
  }
}

async function handleAdd() {
  adding.value = true
  try {
    emit('add', {
      seasons: selectedSeasons.value,
      isUpdate: isUpdate.value
    })
  } finally {
    adding.value = false
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: #1a1a2e;
  border-radius: 12px;
  width: 90%;
  max-width: 400px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid #333;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.25rem;
  color: #fff;
}

.close-btn {
  background: none;
  border: none;
  color: #888;
  font-size: 1.5rem;
  cursor: pointer;
}

.close-btn:hover {
  color: #fff;
}

.modal-body {
  padding: 1.5rem;
  overflow-y: auto;
  flex: 1;
}

.show-info {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.poster {
  width: 60px;
  border-radius: 4px;
}

.show-info h3 {
  margin: 0 0 0.25rem 0;
  color: #fff;
}

.year {
  color: #888;
  margin: 0;
}

.loading {
  color: #888;
  text-align: center;
  padding: 2rem;
}

.seasons-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.season-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  background: #252540;
  border-radius: 6px;
  cursor: pointer;
  color: #fff;
}

.season-item:hover {
  background: #333355;
}

.season-item.select-all {
  background: #1a1a2e;
  border: 1px solid #333;
  margin-bottom: 0.5rem;
}

.season-item input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.episode-count {
  color: #888;
  margin-left: auto;
  font-size: 0.9rem;
}

.modal-footer {
  display: flex;
  gap: 1rem;
  padding: 1rem 1.5rem;
  border-top: 1px solid #333;
}

.btn-cancel, .btn-add {
  flex: 1;
  padding: 0.75rem;
  border-radius: 6px;
  font-size: 1rem;
  cursor: pointer;
  border: none;
}

.btn-cancel {
  background: #333;
  color: #fff;
}

.btn-cancel:hover {
  background: #444;
}

.btn-add {
  background: #e94560;
  color: #fff;
}

.btn-add:hover:not(:disabled) {
  background: #d63850;
}

.btn-add:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Status indicator styles */
.status-indicator {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-indicator.downloaded {
  background: #4ade80;
}

.status-indicator.monitored {
  background: #fbbf24;
}

.status-indicator.available {
  background: #6b7280;
}

.season-item.downloaded,
.season-item.monitored {
  opacity: 0.6;
  cursor: default;
}

.season-item.downloaded:hover,
.season-item.monitored:hover {
  background: #252540;
}

.no-seasons {
  text-align: center;
  color: #888;
  padding: 2rem;
}
</style>
