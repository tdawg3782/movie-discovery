import api from './api'

export const discoverService = {
  getTrendingMovies: (page = 1) => api.get('/discover/movies/trending', { params: { page } }),
  getTrendingShows: (page = 1) => api.get('/discover/shows/trending', { params: { page } }),
  search: (query, page = 1) => api.get('/discover/search', { params: { q: query, page } }),
  getSimilar: (tmdbId, mediaType) => api.get(`/discover/similar/${tmdbId}`, { params: { media_type: mediaType } }),

  // Genre endpoints
  getMovieGenres: async () => {
    const response = await api.get('/genres/movies')
    return response.genres
  },
  getTvGenres: async () => {
    const response = await api.get('/genres/shows')
    return response.genres
  },

  // Filtered discovery endpoints
  discoverMovies: (options = {}) => {
    const params = {}
    if (options.page) params.page = options.page
    if (options.genre) params.genre = options.genre
    if (options.year) params.year = options.year
    if (options.yearGte) params.year_gte = options.yearGte
    if (options.yearLte) params.year_lte = options.yearLte
    if (options.ratingGte) params.rating_gte = options.ratingGte
    if (options.certification) params.certification = options.certification
    if (options.sortBy) params.sort_by = options.sortBy
    return api.get('/discover/movies', { params })
  },
  discoverShows: (options = {}) => {
    const params = {}
    if (options.page) params.page = options.page
    if (options.genre) params.genre = options.genre
    if (options.year) params.year = options.year
    if (options.yearGte) params.year_gte = options.yearGte
    if (options.yearLte) params.year_lte = options.yearLte
    if (options.ratingGte) params.rating_gte = options.ratingGte
    if (options.sortBy) params.sort_by = options.sortBy
    return api.get('/discover/shows', { params })
  },
}
