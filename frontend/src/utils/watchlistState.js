// Pure URL <-> Watchlist view state mapping + list transform (no Vue, no DOM).
// URL keys: type (<-mediaType), status, sort (<-sortBy), dir (<-sortDir).

const DEFAULTS = {
  mediaType: 'all',
  status: 'all',
  sortBy: 'added',
  sortDir: 'desc',
}

const MEDIA_TYPES = ['all', 'movies', 'shows']
const STATUSES = ['all', 'pending', 'added', 'downloading']
const SORT_BYS = ['added', 'title', 'rating', 'release']
const SORT_DIRS = ['asc', 'desc']

function oneOf(value, allowed, fallback) {
  return allowed.includes(value) ? value : fallback
}

export function parseWatchlistState(query) {
  const q = query || {}
  return {
    mediaType: oneOf(q.type, MEDIA_TYPES, DEFAULTS.mediaType),
    status: oneOf(q.status, STATUSES, DEFAULTS.status),
    sortBy: oneOf(q.sort, SORT_BYS, DEFAULTS.sortBy),
    sortDir: oneOf(q.dir, SORT_DIRS, DEFAULTS.sortDir),
  }
}

export function serializeWatchlistState(state) {
  const out = {}
  if (state.mediaType !== DEFAULTS.mediaType) out.type = String(state.mediaType)
  if (state.status !== DEFAULTS.status) out.status = String(state.status)
  if (state.sortBy !== DEFAULTS.sortBy) out.sort = String(state.sortBy)
  if (state.sortDir !== DEFAULTS.sortDir) out.dir = String(state.sortDir)
  return out
}

function isMissing(v) {
  return v == null || v === ''
}

// Build a comparator that pushes "missing" keys last in both directions and
// applies `dirCmp` to present-vs-present pairs.
function nullsLastComparator(keyFn, dirCmp) {
  return (a, b) => {
    const ka = keyFn(a)
    const kb = keyFn(b)
    const ma = isMissing(ka)
    const mb = isMissing(kb)
    if (ma && mb) return 0
    if (ma) return 1
    if (mb) return -1
    return dirCmp(ka, kb)
  }
}

function comparatorFor(state) {
  const asc = state.sortDir === 'asc'
  const sign = asc ? 1 : -1

  switch (state.sortBy) {
    case 'title':
      return nullsLastComparator(
        (i) => i.title,
        (a, b) => sign * a.localeCompare(b, undefined, { sensitivity: 'base' }),
      )
    case 'rating':
      return nullsLastComparator(
        (i) => i.vote_average,
        (a, b) => sign * (a - b),
      )
    case 'release':
      return nullsLastComparator(
        (i) => i.release_date,
        (a, b) => sign * (a < b ? -1 : a > b ? 1 : 0),
      )
    case 'added':
    default:
      return nullsLastComparator(
        (i) => i.added_at,
        (a, b) => sign * (new Date(a).getTime() - new Date(b).getTime()),
      )
  }
}

export function applyWatchlistView(items, state) {
  let out = items.slice()

  if (state.mediaType === 'movies') {
    out = out.filter((i) => i.media_type === 'movie')
  } else if (state.mediaType === 'shows') {
    out = out.filter((i) => i.media_type === 'show')
  }

  if (state.status !== 'all') {
    out = out.filter((i) => i.status === state.status)
  }

  out.sort(comparatorFor(state))
  return out
}
