<template>
  <div class="download-progress">
    <div class="progress-bar">
      <div
        class="progress-fill"
        :style="{ width: `${percentage}%` }"
      ></div>
    </div>
    <div class="progress-info">
      <span class="percentage">{{ percentage }}%</span>
      <span v-if="timeLeft" class="time-left">{{ timeLeft }} remaining</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  size: {
    type: Number,
    default: 0
  },
  sizeLeft: {
    type: Number,
    default: 0
  },
  timeleft: {
    type: String,
    default: ''
  }
})

const percentage = computed(() => {
  if (!props.size || props.size === 0) return 0
  const downloaded = props.size - props.sizeLeft
  return Math.round((downloaded / props.size) * 100)
})

const timeLeft = computed(() => {
  if (!props.timeleft) return null

  // Parse time format (HH:MM:SS or similar)
  const parts = props.timeleft.split(':')
  if (parts.length === 3) {
    const hours = parseInt(parts[0])
    const minutes = parseInt(parts[1])

    if (hours > 0) {
      return `${hours}h ${minutes}m`
    }
    return `${minutes}m`
  }
  return props.timeleft
})
</script>

<style scoped>
.download-progress {
  width: 100%;
}

.progress-bar {
  height: 6px;
  background: #252540;
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #e94560, #ff6b6b);
  border-radius: 3px;
  transition: width 0.3s ease;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  margin-top: 0.25rem;
  font-size: 0.75rem;
  color: #999;
}

.percentage {
  color: #e94560;
}
</style>
