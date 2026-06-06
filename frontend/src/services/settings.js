import api from './api'

export default {
  /**
   * Get current settings (with masked keys)
   */
  async getSettings() {
    return await api.get('/settings')
  },

  /**
   * Update settings
   * @param {Object} settings - Settings to update
   */
  async updateSettings(settings) {
    return await api.put('/settings', settings)
  },

  /**
   * Test connection to a service
   * @param {string} service - 'tmdb', 'radarr', or 'sonarr'
   */
  async testConnection(service) {
    return await api.post('/settings/test', { service })
  },

  /**
   * Get available Radarr quality profiles
   */
  async getRadarrQualityProfiles() {
    return await api.get('/radarr/quality-profiles')
  },

  /**
   * Get available Sonarr quality profiles
   */
  async getSonarrQualityProfiles() {
    return await api.get('/sonarr/quality-profiles')
  }
}
