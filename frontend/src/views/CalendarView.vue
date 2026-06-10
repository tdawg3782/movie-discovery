<template>
  <div class="calendar-view">
    <h1>Coming Soon</h1>

    <div v-if="degraded.length" class="degraded-banner">
      ⚠ {{ degraded.join('/') }} unreachable — showing partial results
    </div>

    <div v-if="loading" class="loading">Loading...</div>

    <div v-else-if="groups.length === 0" class="empty">
      Nothing releasing soon.
    </div>

    <div v-else class="calendar-list">
      <section
        v-for="group in groups"
        :key="group.date"
        class="date-section"
      >
        <h2 class="date-label">{{ group.label }}</h2>
        <div
          v-for="(entry, index) in group.entries"
          :key="`${entry.tmdb_id}-${index}`"
          class="entry"
        >
          <div class="entry-info">
            <div class="entry-title">{{ entry.title }}</div>
            <div v-if="entry.subtitle" class="entry-subtitle">{{ entry.subtitle }}</div>
          </div>
          <span class="badge" :class="{ 'in-library': entry.in_library }">
            {{ entry.in_library ? 'In Library' : entry.source }}
          </span>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { calendarService } from '@/services/calendar'
import { groupByDate } from '@/utils/calendarState'

const loading = ref(true)
const items = ref([])
const degraded = ref([])

const groups = computed(() => groupByDate(items.value))

onMounted(async () => {
  loading.value = true
  try {
    const data = await calendarService.getCalendar()
    items.value = data.items || []
    degraded.value = data.degraded || []
  } catch (error) {
    console.error('Failed to load calendar:', error)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.calendar-view h1 {
  margin-bottom: 20px;
}

.degraded-banner {
  margin-bottom: 16px;
  padding: 8px 12px;
  border-radius: 6px;
  background: #4d3a1f;
  color: #f0c674;
  font-size: 0.85rem;
}

.loading,
.empty {
  padding: 40px;
  text-align: center;
  color: #888;
}

.date-section {
  margin-bottom: 24px;
}

.date-label {
  font-size: 1rem;
  color: #888;
  border-bottom: 1px solid #2a2a2a;
  padding-bottom: 6px;
  margin-bottom: 10px;
}

.entry {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  background: #1a1a1a;
  border-radius: 6px;
  margin-bottom: 6px;
}

.entry-title {
  font-weight: 600;
}

.entry-subtitle {
  font-size: 0.85rem;
  color: #aaa;
}

.badge {
  flex-shrink: 0;
  font-size: 0.75rem;
  text-transform: capitalize;
  padding: 3px 8px;
  border-radius: 4px;
  background: #333;
  color: #ccc;
}

.badge.in-library {
  background: #1f4d2e;
  color: #7fdca0;
}
</style>
