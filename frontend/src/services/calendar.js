import api from './api'

export const calendarService = {
  getCalendar: (start, end) => api.get('/calendar', { params: { start, end } }),
}
