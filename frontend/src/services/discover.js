import api from './api'

export const discoverService = {
  getTrendingMovies: (page = 1) => api.get(`/discover/movies/trending?page=${page}`),
  getTrendingShows: (page = 1) => api.get(`/discover/shows/trending?page=${page}`),
  search: (query, page = 1) => api.get(`/discover/search?q=${query}&page=${page}`),
  getSimilar: (tmdbId, mediaType) => api.get(`/discover/similar/${tmdbId}?media_type=${mediaType}`),
}
