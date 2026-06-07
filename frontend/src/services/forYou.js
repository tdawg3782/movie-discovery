import api from './api'

export const forYouService = {
  getRecommendations: (refresh = false) => api.get('/for-you', { params: refresh ? { refresh: true } : {} }),
}
