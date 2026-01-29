import api from './api'

export const watchlistService = {
  getAll: () => api.get('/watchlist'),

  add: (tmdbId, mediaType, notes = null) =>
    api.post('/watchlist', { tmdb_id: tmdbId, media_type: mediaType, notes }),

  remove: (id) => api.delete(`/watchlist/${id}`),

  /**
   * Process watchlist items (send to Radarr/Sonarr)
   * @param {number[]} ids - TMDB IDs to process
   * @param {string} mediaType - 'movie' or 'tv'
   * @returns {Promise<{processed: number[], failed: Array<{tmdb_id: number, error: string}>}>}
   */
  processItems: (ids, mediaType) =>
    api.post('/watchlist/process', { ids, media_type: mediaType }),

  /**
   * Delete multiple watchlist items
   * @param {number[]} ids - TMDB IDs to delete
   * @returns {Promise<{deleted: number}>}
   */
  deleteItems: (ids) =>
    api.delete('/watchlist/batch', { data: { ids } }),
}
