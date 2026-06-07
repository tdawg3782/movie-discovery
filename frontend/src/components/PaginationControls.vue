<template>
  <div v-if="totalPages > 1" class="pagination-controls">
    <button
      :disabled="currentPage <= 1"
      @click="$emit('change', currentPage - 1)"
    >
      Prev
    </button>
    <span class="page-indicator">Page {{ currentPage }} of {{ totalPages }}</span>
    <button
      :disabled="currentPage >= totalPages"
      @click="$emit('change', currentPage + 1)"
    >
      Next
    </button>
  </div>
</template>

<script setup>
defineProps({
  currentPage: { type: Number, required: true },
  totalPages: { type: Number, required: true }
})

defineEmits(['change'])
</script>

<style scoped>
.pagination-controls {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin: 30px 0;
}

.pagination-controls button {
  padding: 12px 28px;
  border-radius: 6px;
  background: #2a2a2a;
  border: 1px solid #3a3a3a;
  color: #e0e0e0;
  cursor: pointer;
  transition: border-color 0.2s;
}

.pagination-controls button:hover {
  border-color: #e50914;
}

.pagination-controls button:disabled {
  color: #555;
  cursor: not-allowed;
  border-color: #3a3a3a;
}

.page-indicator {
  color: #888;
  font-size: 14px;
}
</style>
