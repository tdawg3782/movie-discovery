import api from './api'

export const libraryService = {
  getMovieStatus: (tmdbId) => api.get(`/radarr/status/${tmdbId}`),
  addMovie: (tmdbId) => api.post('/radarr/add', { tmdb_id: tmdbId }),
  getShowStatus: (tmdbId) => api.get(`/sonarr/status/${tmdbId}`),
  addShow: (tmdbId) => api.post('/sonarr/add', { tmdb_id: tmdbId }),

  // Batch status checking
  getBatchMovieStatus: (tmdbIds) => api.post('/radarr/status/batch', { tmdb_ids: tmdbIds }),
  getBatchShowStatus: (tmdbIds) => api.post('/sonarr/status/batch', { tmdb_ids: tmdbIds }),

  // Activity and queue
  getActivity: (limit = 20) => api.get(`/library/activity?limit=${limit}`),
  getQueue: () => api.get('/library/queue'),
  getRadarrQueue: () => api.get('/radarr/queue'),
  getSonarrQueue: () => api.get('/sonarr/queue'),
  getRecentMovies: (limit = 20) => api.get(`/radarr/recent?limit=${limit}`),
  getRecentShows: (limit = 20) => api.get(`/sonarr/recent?limit=${limit}`),
}
