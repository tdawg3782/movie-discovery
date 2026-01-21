<template>
  <span :class="['badge', status]">
    {{ label }}
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: { type: String, default: null }
})

const label = computed(() => {
  switch (props.status) {
    case 'available': return 'In Library'
    case 'downloading': return 'Downloading'
    case 'added': return 'Added'
    default: return 'Add'
  }
})
</script>

<style scoped>
.badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}
.available { background: #22c55e; color: white; }
.downloading { background: #eab308; color: black; }
.added { background: #3b82f6; color: white; }
.badge:not(.available):not(.downloading):not(.added) {
  background: #e50914;
  color: white;
  cursor: pointer;
}
</style>
