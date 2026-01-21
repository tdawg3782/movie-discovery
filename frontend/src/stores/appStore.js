import { defineStore } from 'pinia'
import { discoverService } from '@/services/discover'
import { libraryService } from '@/services/library'
import { watchlistService } from '@/services/watchlist'

export const useAppStore = defineStore('app', {
  state: () => ({
    trendingMovies: [],
    trendingShows: [],
    searchResults: [],
    watchlist: [],
    loading: false,
    error: null,
  }),

  actions: {
    async fetchTrendingMovies() {
      this.loading = true
      try {
        const data = await discoverService.getTrendingMovies()
        this.trendingMovies = data.results
      } catch (e) {
        this.error = e.message
      } finally {
        this.loading = false
      }
    },

    async addToLibrary(media) {
      try {
        if (media.media_type === 'movie') {
          await libraryService.addMovie(media.tmdb_id)
        } else {
          await libraryService.addShow(media.tmdb_id)
        }
        media.library_status = 'added'
      } catch (e) {
        this.error = e.message
      }
    },

    async fetchWatchlist() {
      const data = await watchlistService.getAll()
      this.watchlist = data.items
    },
  },
})
