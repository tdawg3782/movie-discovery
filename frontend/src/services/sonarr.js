import api from './api'

export const sonarrService = {
  /**
   * Get season status for a series in Sonarr
   * @param {number} tmdbId - TMDB ID of the series
   * @returns {Promise<{in_library: boolean, sonarr_id: number, seasons: Array}>}
   */
  getSeriesSeasons: (tmdbId) => api.get(`/sonarr/series/${tmdbId}/seasons`),
}
