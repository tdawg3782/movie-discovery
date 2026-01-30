<template>
  <div v-if="isOpen" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal">
      <div class="modal-header">
        <h2>Add to Watchlist</h2>
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
          <label class="season-item select-all">
            <input
              type="checkbox"
              :checked="allSelected"
              :indeterminate.prop="someSelected && !allSelected"
              @change="toggleAll"
            />
            <span>Select All</span>
          </label>

          <label
            v-for="season in filteredSeasons"
            :key="season.season_number"
            class="season-item"
          >
            <input
              type="checkbox"
              :checked="isSelected(season.season_number)"
              @change="toggleSeason(season.season_number)"
            />
            <span>Season {{ season.season_number }}</span>
            <span class="episode-count">({{ season.episode_count }} episodes)</span>
          </label>
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn-cancel" @click="$emit('close')">Cancel</button>
        <button
          class="btn-add"
          @click="handleAdd"
          :disabled="selectedSeasons.length === 0 || adding"
        >
          {{ adding ? 'Adding...' : 'Add to Watchlist' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  isOpen: { type: Boolean, default: false },
  show: { type: Object, required: true }
})

const emit = defineEmits(['close', 'add'])

const loading = ref(false)
const adding = ref(false)
const selectedSeasons = ref([])

// Filter out season 0 (specials)
const filteredSeasons = computed(() =>
  (props.show.seasons || []).filter(s => s.season_number > 0)
)

const releaseYear = computed(() => {
  const date = props.show.first_air_date
  return date ? new Date(date).getFullYear() : ''
})

const allSelected = computed(() =>
  filteredSeasons.value.length > 0 &&
  filteredSeasons.value.every(s => selectedSeasons.value.includes(s.season_number))
)

const someSelected = computed(() =>
  selectedSeasons.value.length > 0
)

// Initialize with all seasons selected when modal opens
watch(() => props.isOpen, (open) => {
  if (open) {
    selectedSeasons.value = filteredSeasons.value.map(s => s.season_number)
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
    selectedSeasons.value = filteredSeasons.value.map(s => s.season_number)
  }
}

async function handleAdd() {
  adding.value = true
  try {
    emit('add', selectedSeasons.value)
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
</style>
