import api from './api'

export const libraryService = {
  getMovieStatus: (tmdbId) => api.get(`/radarr/status/${tmdbId}`),
  addMovie: (tmdbId) => api.post('/radarr/add', { tmdb_id: tmdbId }),
  getShowStatus: (tmdbId) => api.get(`/sonarr/status/${tmdbId}`),
  addShow: (tmdbId) => api.post('/sonarr/add', { tmdb_id: tmdbId }),
}
