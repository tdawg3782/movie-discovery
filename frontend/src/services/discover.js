import api from './api'

export const discoverService = {
  getTrendingMovies: (page = 1) => api.get('/discover/movies/trending', { params: { page } }),
  getTrendingShows: (page = 1) => api.get('/discover/shows/trending', { params: { page } }),
  search: (query, page = 1) => api.get('/discover/search', { params: { q: query, page } }),
  getSimilar: (tmdbId, mediaType) => api.get(`/discover/similar/${tmdbId}`, { params: { media_type: mediaType } }),
}
