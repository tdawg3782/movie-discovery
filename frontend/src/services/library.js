import api from './api'

export const libraryService = {
  // Batch status checking
  getBatchMovieStatus: (tmdbIds) => api.post('/radarr/status/batch', { tmdb_ids: tmdbIds }),
  getBatchShowStatus: (tmdbIds) => api.post('/sonarr/status/batch', { tmdb_ids: tmdbIds }),

  // Activity and queue
  getActivity: (limit = 20) => api.get(`/library/activity?limit=${limit}`),
  getQueue: () => api.get('/library/queue'),
}
