// Pure URL <-> Discover view state mapping (no Vue, no DOM).
// The search query key in the URL is `q` (matches the backend search param);
// it maps to/from the canonical state's `search` field.

function nonEmptyString(v) {
  return typeof v === 'string' && v.length > 0 ? v : null
}

function numberOrNull(v) {
  if (typeof v !== 'string' || v.length === 0) return null
  const n = Number(v)
  return Number.isFinite(n) ? n : null
}

export function parseDiscoverState(query) {
  const q = query || {}

  const rawPage = q.page
  const page = typeof rawPage === 'string' && /^\d+$/.test(rawPage) ? Number(rawPage) : NaN

  return {
    tab: q.tab === 'shows' ? 'shows' : 'movies',
    page: Number.isInteger(page) && page >= 1 ? page : 1,
    search: typeof q.q === 'string' ? q.q : '',
    filters: {
      genre: nonEmptyString(q.genre),
      yearGte: numberOrNull(q.yearGte),
      yearLte: numberOrNull(q.yearLte),
      ratingGte: numberOrNull(q.ratingGte),
      certification: nonEmptyString(q.certification),
      sortBy: nonEmptyString(q.sortBy) || 'popularity.desc',
      inLibrary: q.inLibrary === 'true',
      notInLibrary: q.notInLibrary === 'true',
    },
  }
}

export function serializeDiscoverState(state) {
  const out = {}
  const filters = state.filters || {}

  if (state.tab === 'shows') out.tab = 'shows'
  if (state.page > 1) out.page = String(state.page)
  if (typeof state.search === 'string' && state.search.length > 0) out.q = state.search

  if (filters.genre) out.genre = filters.genre
  if (filters.yearGte != null) out.yearGte = String(filters.yearGte)
  if (filters.yearLte != null) out.yearLte = String(filters.yearLte)
  if (filters.ratingGte != null) out.ratingGte = String(filters.ratingGte)
  if (filters.certification) out.certification = filters.certification
  if (filters.sortBy && filters.sortBy !== 'popularity.desc') out.sortBy = filters.sortBy
  if (filters.inLibrary === true) out.inLibrary = 'true'
  if (filters.notInLibrary === true) out.notInLibrary = 'true'

  return out
}

export function clampPage(page, totalPages) {
  return Math.min(Math.max(page, 1), Math.max(totalPages, 1))
}
