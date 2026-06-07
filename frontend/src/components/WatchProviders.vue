<template>
  <div v-if="hasProviders" class="watch-providers">
    <h3>Where to Watch ({{ providers.region }})</h3>
    <div class="providers-row">
      <a
        v-for="p in streamItems"
        :key="p.provider_id"
        :href="providers.link"
        target="_blank"
        rel="noopener"
        :title="p.provider_name"
        class="provider"
      >
        <img
          v-if="p.logo_path"
          :src="`https://image.tmdb.org/t/p/w92${p.logo_path}`"
          :alt="p.provider_name"
        />
        <span v-else class="provider-name">{{ p.provider_name }}</span>
      </a>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  providers: {
    type: Object,
    default: null
  }
})

const streamItems = computed(() => [
  ...(props.providers?.flatrate || []),
  ...(props.providers?.free || [])
])

const hasProviders = computed(() => streamItems.value.length > 0)
</script>

<style scoped>
.watch-providers {
  margin-top: 1.5rem;
}

.watch-providers h3 {
  margin: 0 0 0.75rem;
  font-size: 1.1rem;
}

.providers-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: center;
}

.provider {
  display: inline-flex;
  align-items: center;
  text-decoration: none;
  color: inherit;
}

.provider img {
  width: 46px;
  height: 46px;
  border-radius: 8px;
  object-fit: cover;
  display: block;
}

.provider-name {
  padding: 0.4rem 0.6rem;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.1);
  font-size: 0.85rem;
}
</style>
