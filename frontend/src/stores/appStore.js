// Pinia store placeholder — currently unused.
// Views manage their own local state via services directly.
// If cross-view shared state is needed in the future (e.g., watchlist count badge),
// define store actions here and import in the relevant views.

import { defineStore } from 'pinia'

export const useAppStore = defineStore('app', {
  state: () => ({
    // Add shared cross-view state here as needed
  }),
})
