import api from './api'

export const watchlistService = {
  getAll: () => api.get('/watchlist'),
  add: (tmdbId, mediaType, notes = null) =>
    api.post('/watchlist', { tmdb_id: tmdbId, media_type: mediaType, notes }),
  remove: (id) => api.delete(`/watchlist/${id}`),
}
