<template>
  <div class="watchlist-view">
    <div class="watchlist-header">
      <h2>My Watchlist</h2>

      <!-- Batch Actions -->
      <div v-if="selectedItems.length > 0" class="batch-actions">
        <span class="selection-count">{{ selectedItems.length }} selected</span>
        <button class="btn-process" @click="showProcessModal = true">
          Add to Library
        </button>
        <button class="btn-batch-delete" @click="confirmBatchDelete">
          Remove
        </button>
      </div>
    </div>

    <!-- Filter Tabs -->
    <div class="filter-tabs">
      <button
        :class="['tab', { active: filter === 'all' }]"
        @click="filter = 'all'"
      >
        All ({{ items.length }})
      </button>
      <button
        :class="['tab', { active: filter === 'movies' }]"
        @click="filter = 'movies'"
      >
        Movies ({{ movieCount }})
      </button>
      <button
        :class="['tab', { active: filter === 'shows' }]"
        @click="filter = 'shows'"
      >
        TV Shows ({{ showCount }})
      </button>
    </div>

    <div v-if="loading" class="loading">Loading watchlist...</div>

    <div v-else-if="error" class="error">
      <p>{{ error }}</p>
      <button @click="fetchWatchlist">Retry</button>
    </div>

    <div v-else-if="items.length === 0" class="empty">
      <p>Your watchlist is empty.</p>
      <router-link to="/" class="discover-link">Discover movies and shows</router-link>
    </div>

    <template v-else>
      <!-- Select All -->
      <div v-if="filteredItems.length > 0" class="select-all">
        <label>
          <input
            type="checkbox"
            :checked="allSelected"
            @change="toggleSelectAll"
          />
          Select All
        </label>
      </div>

      <!-- Watchlist Items -->
      <div class="watchlist-grid">
        <div
          v-for="item in filteredItems"
          :key="item.id"
          :class="['watchlist-item-wrapper', { expanded: isExpanded(item.tmdb_id) }]"
        >
          <div
            :class="['watchlist-item', { selected: isSelected(item.tmdb_id), expandable: item.media_type === 'show' }]"
            @click="toggleExpand(item)"
          >
            <div class="item-checkbox" @click.stop>
              <input
                type="checkbox"
                :checked="isSelected(item.tmdb_id)"
                @change="toggleSelect(item)"
              />
            </div>

            <router-link
              :to="`/${item.media_type === 'movie' ? 'movie' : 'tv'}/${item.tmdb_id}`"
              class="item-poster"
              @click.stop
            >
              <img
                v-if="item.poster_path"
                :src="`https://image.tmdb.org/t/p/w185${item.poster_path}`"
                :alt="item.title"
              />
              <div v-else class="no-poster">?</div>
            </router-link>

            <div class="item-info">
              <router-link
                :to="`/${item.media_type === 'movie' ? 'movie' : 'tv'}/${item.tmdb_id}`"
                class="item-title"
                @click.stop
              >
                {{ item.title }}
              </router-link>
              <div class="item-meta">
                <span class="media-type">{{ item.media_type === 'movie' ? 'Movie' : 'TV Show' }}</span>
                <span :class="['status-badge', item.status]">{{ formatStatus(item.status) }}</span>
                <span
                  v-if="item.media_type === 'show' && item.total_seasons"
                  :class="['seasons-summary', { 'is-update': item.is_season_update }]"
                >
                  {{ formatSeasonsSummary(item) }}
                </span>
              </div>
              <div v-if="item.notes" class="item-notes">{{ item.notes }}</div>
              <div class="item-date">Added {{ formatDate(item.added_at) }}</div>
            </div>

            <div class="item-actions" @click.stop>
              <button
                v-if="item.media_type === 'show'"
                class="btn-expand"
                @click.stop="toggleExpand(item)"
                :title="isExpanded(item.tmdb_id) ? 'Collapse' : 'Edit Seasons'"
              >
                <span :class="['expand-icon', { rotated: isExpanded(item.tmdb_id) }]">&#9660;</span>
              </button>
              <button
                v-if="item.status === 'pending'"
                class="btn-add-single"
                @click="processSingle(item)"
                :disabled="processing"
                title="Add to Library"
              >
                +
              </button>
              <button
                class="btn-remove-single"
                @click="removeSingle(item.id)"
                :disabled="removing === item.id"
                title="Remove"
              >
                ×
              </button>
            </div>
          </div>

          <!-- Expanded Season Selection -->
          <div v-if="item.media_type === 'show' && isExpanded(item.tmdb_id)" class="season-selector">
            <div class="season-selector-header">
              <span class="season-selector-title">Select Seasons to Monitor</span>
              <button
                class="btn-select-all-seasons"
                @click="toggleAllSeasons(item)"
              >
                {{ areAllSeasonsSelected(item) ? 'Deselect All' : 'Select All' }}
              </button>
            </div>
            <div class="season-checkboxes">
              <label
                v-for="season in item.total_seasons"
                :key="season"
                class="season-checkbox"
              >
                <input
                  type="checkbox"
                  :checked="isSeasonSelected(item, season)"
                  @change="toggleSeason(item, season)"
                />
                <span class="season-label">Season {{ season }}</span>
              </label>
            </div>
            <div class="season-selector-actions">
              <button
                class="btn-save-seasons"
                @click="saveSeasons(item)"
                :disabled="savingSeasons"
              >
                {{ savingSeasons ? 'Saving...' : 'Save Changes' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- Process Modal -->
    <Teleport to="body">
      <div v-if="showProcessModal" class="modal-overlay" @click="closeModal">
        <div class="modal-content" @click.stop>
          <h3>Add to Library</h3>
          <p>Add {{ selectedItems.length }} item(s) to your library?</p>

          <div class="modal-summary">
            <div v-if="selectedMovieIds.length">
              <strong>Movies:</strong> {{ selectedMovieIds.length }} → Radarr
            </div>
            <div v-if="selectedShowIds.length">
              <strong>TV Shows:</strong> {{ selectedShowIds.length }} → Sonarr
            </div>
          </div>

          <div class="modal-actions">
            <button class="btn-cancel" @click="closeModal">Cancel</button>
            <button class="btn-confirm" @click="processSelected" :disabled="processing">
              {{ processing ? 'Processing...' : 'Confirm' }}
            </button>
          </div>

          <div v-if="processResult" class="process-result">
            <div v-if="processResult.processed.length" class="success">
              ✓ {{ processResult.processed.length }} added successfully
            </div>
            <div v-if="processResult.failed.length" class="errors">
              ✗ {{ processResult.failed.length }} failed
              <ul>
                <li v-for="fail in processResult.failed" :key="fail.tmdb_id">
                  {{ fail.error }}
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { watchlistService } from '../services/watchlist'

const items = ref([])
const loading = ref(false)
const error = ref(null)
const removing = ref(null)
const processing = ref(false)

const selectedItems = ref([]) // Array of {tmdb_id, media_type}
const filter = ref('all')
const showProcessModal = ref(false)
const processResult = ref(null)

// Expandable row state for TV shows
const expandedItem = ref(null)
const savingSeasons = ref(false)
// Local state for pending season changes (keyed by tmdb_id)
const pendingSeasonChanges = ref({})

onMounted(() => {
  fetchWatchlist()
})

const fetchWatchlist = async () => {
  loading.value = true
  error.value = null

  try {
    const response = await watchlistService.getAll()
    items.value = response.items || []
  } catch (err) {
    error.value = err.response?.data?.detail || 'Failed to load watchlist'
    items.value = []
  } finally {
    loading.value = false
  }
}

const filteredItems = computed(() => {
  if (filter.value === 'movies') {
    return items.value.filter(i => i.media_type === 'movie')
  }
  if (filter.value === 'shows') {
    return items.value.filter(i => i.media_type === 'show')
  }
  return items.value
})

const movieCount = computed(() =>
  items.value.filter(i => i.media_type === 'movie').length
)

const showCount = computed(() =>
  items.value.filter(i => i.media_type === 'show').length
)

const allSelected = computed(() =>
  filteredItems.value.length > 0 &&
  filteredItems.value.every(i => isSelected(i.tmdb_id))
)

const selectedMovieIds = computed(() =>
  selectedItems.value
    .filter(s => s.media_type === 'movie')
    .map(s => s.tmdb_id)
)

const selectedShowIds = computed(() =>
  selectedItems.value
    .filter(s => s.media_type === 'show')
    .map(s => s.tmdb_id)
)

function isSelected(tmdbId) {
  return selectedItems.value.some(s => s.tmdb_id === tmdbId)
}

function toggleSelect(item) {
  const index = selectedItems.value.findIndex(s => s.tmdb_id === item.tmdb_id)
  if (index === -1) {
    selectedItems.value.push({ tmdb_id: item.tmdb_id, media_type: item.media_type })
  } else {
    selectedItems.value.splice(index, 1)
  }
}

function toggleSelectAll() {
  if (allSelected.value) {
    // Deselect all filtered items
    const filteredIds = new Set(filteredItems.value.map(i => i.tmdb_id))
    selectedItems.value = selectedItems.value.filter(s => !filteredIds.has(s.tmdb_id))
  } else {
    // Select all filtered items
    const existing = new Set(selectedItems.value.map(s => s.tmdb_id))
    for (const item of filteredItems.value) {
      if (!existing.has(item.tmdb_id)) {
        selectedItems.value.push({ tmdb_id: item.tmdb_id, media_type: item.media_type })
      }
    }
  }
}

async function processSelected() {
  processing.value = true
  processResult.value = { processed: [], failed: [] }

  try {
    // Process movies
    if (selectedMovieIds.value.length > 0) {
      const result = await watchlistService.processItems(selectedMovieIds.value, 'movie')
      processResult.value.processed.push(...result.processed)
      processResult.value.failed.push(...result.failed)
    }

    // Process shows
    if (selectedShowIds.value.length > 0) {
      const result = await watchlistService.processItems(selectedShowIds.value, 'tv')
      processResult.value.processed.push(...result.processed)
      processResult.value.failed.push(...result.failed)
    }

    // Refresh list and clear selection
    await fetchWatchlist()
    selectedItems.value = []

  } catch (err) {
    console.error('Process failed:', err)
    processResult.value.failed.push({ tmdb_id: 0, error: err.message || 'Processing failed' })
  } finally {
    processing.value = false
  }
}

async function processSingle(item) {
  processing.value = true
  try {
    await watchlistService.processItems([item.tmdb_id], item.media_type)
    await fetchWatchlist()
  } catch (err) {
    console.error('Failed to process:', err)
    alert(err.response?.data?.detail || 'Failed to add to library')
  } finally {
    processing.value = false
  }
}

async function confirmBatchDelete() {
  if (confirm(`Remove ${selectedItems.value.length} item(s) from watchlist?`)) {
    try {
      const ids = selectedItems.value.map(s => s.tmdb_id)
      await watchlistService.deleteItems(ids)
      await fetchWatchlist()
      selectedItems.value = []
    } catch (err) {
      console.error('Batch delete failed:', err)
      alert(err.response?.data?.detail || 'Failed to remove items')
    }
  }
}

async function removeSingle(id) {
  removing.value = id
  try {
    await watchlistService.remove(id)
    items.value = items.value.filter(item => item.id !== id)
  } catch (err) {
    console.error('Failed to remove from watchlist:', err)
    alert(err.response?.data?.detail || 'Failed to remove from watchlist')
  } finally {
    removing.value = null
  }
}

function closeModal() {
  showProcessModal.value = false
  processResult.value = null
}

function formatStatus(status) {
  const labels = {
    pending: 'Pending',
    added: 'In Library',
    downloading: 'Downloading'
  }
  return labels[status] || status
}

function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString()
}

// Expandable row functions for TV shows
function toggleExpand(item) {
  if (item.media_type !== 'show') return
  if (expandedItem.value === item.tmdb_id) {
    expandedItem.value = null
  } else {
    expandedItem.value = item.tmdb_id
    // Initialize pending changes with current selection
    if (!pendingSeasonChanges.value[item.tmdb_id]) {
      pendingSeasonChanges.value[item.tmdb_id] = item.selected_seasons
        ? [...item.selected_seasons]
        : Array.from({ length: item.total_seasons }, (_, i) => i + 1)
    }
  }
}

function isExpanded(tmdbId) {
  return expandedItem.value === tmdbId
}

function getSelectedSeasons(item) {
  // Return pending changes if they exist, otherwise the item's current selection
  if (pendingSeasonChanges.value[item.tmdb_id]) {
    return pendingSeasonChanges.value[item.tmdb_id]
  }
  return item.selected_seasons || Array.from({ length: item.total_seasons }, (_, i) => i + 1)
}

function isSeasonSelected(item, season) {
  const selected = getSelectedSeasons(item)
  return selected.includes(season)
}

function toggleSeason(item, season) {
  const tmdbId = item.tmdb_id
  if (!pendingSeasonChanges.value[tmdbId]) {
    pendingSeasonChanges.value[tmdbId] = item.selected_seasons
      ? [...item.selected_seasons]
      : Array.from({ length: item.total_seasons }, (_, i) => i + 1)
  }

  const selected = pendingSeasonChanges.value[tmdbId]
  const index = selected.indexOf(season)
  if (index === -1) {
    selected.push(season)
    selected.sort((a, b) => a - b)
  } else {
    selected.splice(index, 1)
  }
}

function areAllSeasonsSelected(item) {
  const selected = getSelectedSeasons(item)
  return selected.length === item.total_seasons
}

function toggleAllSeasons(item) {
  const tmdbId = item.tmdb_id
  if (areAllSeasonsSelected(item)) {
    // Deselect all - but keep at least season 1
    pendingSeasonChanges.value[tmdbId] = [1]
  } else {
    // Select all
    pendingSeasonChanges.value[tmdbId] = Array.from({ length: item.total_seasons }, (_, i) => i + 1)
  }
}

async function saveSeasons(item) {
  const tmdbId = item.tmdb_id
  const selectedSeasons = pendingSeasonChanges.value[tmdbId]

  if (!selectedSeasons || selectedSeasons.length === 0) {
    alert('Please select at least one season')
    return
  }

  savingSeasons.value = true
  try {
    await watchlistService.updateSeasons(tmdbId, selectedSeasons)
    await fetchWatchlist()
    // Clear pending changes after successful save
    delete pendingSeasonChanges.value[tmdbId]
  } catch (err) {
    console.error('Failed to update seasons:', err)
    alert(err.response?.data?.detail || 'Failed to update seasons')
  } finally {
    savingSeasons.value = false
  }
}

function formatSeasonsSummary(item) {
  const selected = item.selected_seasons || []
  const total = item.total_seasons || 0

  if (total === 0) return ''

  // If this is a season update, show with + prefix
  if (item.is_season_update) {
    if (selected.length === 0) return ''
    return `+Seasons ${selected.join(', ')}`
  }

  // Regular new show - show fraction or "All seasons"
  if (selected.length === 0 || selected.length === total) {
    return 'All seasons'
  }
  return `${selected.length} of ${total} seasons`
}
</script>

<style scoped>
.watchlist-view {
  padding: 20px 0;
}

.watchlist-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 16px;
}

.watchlist-header h2 {
  margin: 0;
  font-size: 24px;
}

.batch-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.selection-count {
  color: #888;
  font-size: 14px;
}

.btn-process {
  padding: 8px 16px;
  background: #e50914;
  border: none;
  border-radius: 4px;
  color: #fff;
  cursor: pointer;
  font-size: 14px;
}

.btn-process:hover {
  background: #f40d17;
}

.btn-batch-delete {
  padding: 8px 16px;
  background: transparent;
  border: 1px solid #666;
  border-radius: 4px;
  color: #ccc;
  cursor: pointer;
  font-size: 14px;
}

.btn-batch-delete:hover {
  border-color: #e50914;
  color: #e50914;
}

.filter-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.tab {
  padding: 8px 16px;
  background: transparent;
  border: 1px solid #333;
  border-radius: 4px;
  color: #ccc;
  cursor: pointer;
  font-size: 14px;
}

.tab:hover {
  border-color: #666;
}

.tab.active {
  background: #222;
  border-color: #e50914;
  color: #fff;
}

.select-all {
  margin-bottom: 16px;
  color: #ccc;
  font-size: 14px;
}

.select-all input {
  margin-right: 8px;
}

.watchlist-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.watchlist-item {
  display: flex;
  gap: 16px;
  padding: 16px;
  background: #1a1a1a;
  border-radius: 8px;
  border: 2px solid transparent;
  transition: border-color 0.2s;
}

.watchlist-item.selected {
  border-color: #e50914;
}

.item-checkbox {
  display: flex;
  align-items: center;
}

.item-checkbox input {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.item-poster {
  flex: 0 0 auto;
}

.item-poster img {
  width: 80px;
  border-radius: 4px;
}

.no-poster {
  width: 80px;
  height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #333;
  border-radius: 4px;
  color: #666;
  font-size: 24px;
}

.item-info {
  flex: 1;
  min-width: 0;
}

.item-title {
  color: #fff;
  text-decoration: none;
  font-size: 16px;
  font-weight: 500;
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-title:hover {
  color: #e50914;
}

.item-meta {
  display: flex;
  gap: 8px;
  margin-top: 8px;
  align-items: center;
}

.media-type {
  font-size: 12px;
  color: #888;
}

.status-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  text-transform: uppercase;
}

.status-badge.pending {
  background: #333;
  color: #ccc;
}

.status-badge.added {
  background: rgba(76, 175, 80, 0.2);
  color: #4caf50;
}

.status-badge.downloading {
  background: rgba(33, 150, 243, 0.2);
  color: #2196f3;
}

.item-notes {
  font-size: 13px;
  color: #888;
  font-style: italic;
  margin-top: 6px;
}

.item-date {
  font-size: 12px;
  color: #666;
  margin-top: 6px;
}

.item-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.btn-add-single,
.btn-remove-single {
  width: 32px;
  height: 32px;
  padding: 0;
  background: transparent;
  border: 1px solid #444;
  border-radius: 4px;
  cursor: pointer;
  font-size: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.btn-add-single {
  color: #4caf50;
}

.btn-add-single:hover:not(:disabled) {
  border-color: #4caf50;
  background: rgba(76, 175, 80, 0.1);
}

.btn-remove-single {
  color: #888;
}

.btn-remove-single:hover:not(:disabled) {
  border-color: #e50914;
  color: #e50914;
}

.btn-add-single:disabled,
.btn-remove-single:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.loading,
.error,
.empty {
  text-align: center;
  padding: 60px 20px;
  color: #888;
}

.error {
  color: #e50914;
}

.error button,
.discover-link {
  display: inline-block;
  margin-top: 16px;
  padding: 8px 20px;
  background: #e50914;
  border: none;
  border-radius: 4px;
  color: white;
  text-decoration: none;
  cursor: pointer;
}

.error button:hover,
.discover-link:hover {
  background: #f40d17;
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: #1a1a1a;
  padding: 24px;
  border-radius: 8px;
  max-width: 400px;
  width: 90%;
}

.modal-content h3 {
  color: #fff;
  margin: 0 0 16px;
  font-size: 20px;
}

.modal-content p {
  color: #ccc;
  margin-bottom: 16px;
}

.modal-summary {
  background: #252525;
  padding: 12px 16px;
  border-radius: 4px;
  margin-bottom: 20px;
  color: #ccc;
  font-size: 14px;
}

.modal-summary div {
  margin: 4px 0;
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.btn-cancel {
  padding: 10px 20px;
  background: transparent;
  border: 1px solid #666;
  border-radius: 4px;
  color: #ccc;
  cursor: pointer;
}

.btn-cancel:hover {
  border-color: #888;
}

.btn-confirm {
  padding: 10px 20px;
  background: #e50914;
  border: none;
  border-radius: 4px;
  color: #fff;
  cursor: pointer;
}

.btn-confirm:hover:not(:disabled) {
  background: #f40d17;
}

.btn-confirm:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.process-result {
  margin-top: 16px;
  padding: 12px;
  border-radius: 4px;
  font-size: 14px;
}

.process-result .success {
  color: #4caf50;
  margin-bottom: 8px;
}

.process-result .errors {
  color: #e50914;
}

.process-result ul {
  margin: 8px 0 0 20px;
  padding: 0;
  font-size: 12px;
}

/* Expandable Row Styles */
.watchlist-item-wrapper {
  background: #1a1a2e;
  border-radius: 8px;
  border: 2px solid transparent;
  transition: border-color 0.2s;
  overflow: hidden;
}

.watchlist-item-wrapper.expanded {
  border-color: #252540;
}

.watchlist-item {
  display: flex;
  gap: 16px;
  padding: 16px;
  background: #1a1a2e;
  transition: background-color 0.2s;
}

.watchlist-item.expandable {
  cursor: pointer;
}

.watchlist-item.expandable:hover {
  background: #252540;
}

.watchlist-item.selected {
  background: rgba(233, 69, 96, 0.1);
}

.watchlist-item-wrapper:has(.watchlist-item.selected) {
  border-color: #e94560;
}

.btn-expand {
  width: 32px;
  height: 32px;
  padding: 0;
  background: transparent;
  border: 1px solid #444;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  color: #888;
}

.btn-expand:hover {
  border-color: #e94560;
  color: #e94560;
}

.expand-icon {
  font-size: 10px;
  transition: transform 0.2s;
  display: inline-block;
}

.expand-icon.rotated {
  transform: rotate(180deg);
}

.seasons-summary {
  font-size: 12px;
  color: #e94560;
  background: rgba(233, 69, 96, 0.15);
  padding: 2px 8px;
  border-radius: 10px;
}

.seasons-summary.is-update {
  background: rgba(74, 222, 128, 0.15);
  color: #4ade80;
}

/* Season Selector Panel */
.season-selector {
  padding: 16px 16px 16px 130px;
  background: #252540;
  border-top: 1px solid #333;
}

.season-selector-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.season-selector-title {
  font-size: 14px;
  color: #ccc;
  font-weight: 500;
}

.btn-select-all-seasons {
  padding: 4px 12px;
  background: transparent;
  border: 1px solid #444;
  border-radius: 4px;
  color: #ccc;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}

.btn-select-all-seasons:hover {
  border-color: #e94560;
  color: #e94560;
}

.season-checkboxes {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.season-checkbox {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: #1a1a2e;
  border: 1px solid #333;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.season-checkbox:hover {
  border-color: #e94560;
}

.season-checkbox input {
  width: 14px;
  height: 14px;
  cursor: pointer;
  accent-color: #e94560;
}

.season-checkbox input:checked + .season-label {
  color: #fff;
}

.season-label {
  font-size: 13px;
  color: #888;
  white-space: nowrap;
}

.season-selector-actions {
  display: flex;
  justify-content: flex-end;
}

.btn-save-seasons {
  padding: 8px 20px;
  background: #e94560;
  border: none;
  border-radius: 4px;
  color: #fff;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.btn-save-seasons:hover:not(:disabled) {
  background: #f05f7a;
}

.btn-save-seasons:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Responsive adjustments for season selector */
@media (max-width: 600px) {
  .season-selector {
    padding: 16px;
  }

  .season-checkboxes {
    gap: 6px;
  }

  .season-checkbox {
    padding: 4px 8px;
  }

  .season-label {
    font-size: 12px;
  }
}
</style>
