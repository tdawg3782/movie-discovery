// Pure URL <-> Watchlist view state mapping + list transform (no Vue, no DOM).
// URL keys: type (<-mediaType), status, sort (<-sortBy), dir (<-sortDir).

const DEFAULTS = {
  mediaType: 'all',
  status: 'all',
  sortBy: 'added',
  sortDir: 'desc',
  groupBy: 'none',
}

const MEDIA_TYPES = ['all', 'movies', 'shows']
const STATUSES = ['all', 'pending', 'added', 'downloading']
const SORT_BYS = ['added', 'title', 'rating', 'release']
const SORT_DIRS = ['asc', 'desc']
const GROUP_BYS = ['none', 'priority']

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
    groupBy: oneOf(q.group, GROUP_BYS, DEFAULTS.groupBy),
  }
}

export function serializeWatchlistState(state) {
  const out = {}
  if (state.mediaType !== DEFAULTS.mediaType) out.type = String(state.mediaType)
  if (state.status !== DEFAULTS.status) out.status = String(state.status)
  if (state.sortBy !== DEFAULTS.sortBy) out.sort = String(state.sortBy)
  if (state.sortDir !== DEFAULTS.sortDir) out.dir = String(state.sortDir)
  const groupBy = state.groupBy ?? DEFAULTS.groupBy
  if (groupBy !== DEFAULTS.groupBy) out.group = String(groupBy)
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

export const PRIORITY_LABELS = { 1: 'High', 0: 'Normal', '-1': 'Low' }

export function priorityLabel(p) {
  return PRIORITY_LABELS[p] ?? 'Normal'
}

export function parseTagsInput(str) {
  const seen = new Set()
  const out = []
  for (const raw of String(str ?? '').split(',')) {
    const tag = raw.trim()
    if (!tag || seen.has(tag)) continue
    seen.add(tag)
    out.push(tag)
  }
  return out
}

export function formatTags(arr) {
  return arr.join(', ')
}

// Filter + sort via applyWatchlistView, then bucket into priority sections
// (High -> Normal -> Low), preserving the sort order within each and omitting
// empty sections. Items without a `priority` fall into the Normal (0) section.
export function groupWatchlistView(items, state) {
  const sorted = applyWatchlistView(items, state)
  const buckets = new Map([
    [1, []],
    [0, []],
    [-1, []],
  ])
  for (const item of sorted) {
    const bucket = buckets.get(item.priority ?? 0) ?? buckets.get(0)
    bucket.push(item)
  }
  const out = []
  for (const key of [1, 0, -1]) {
    const sectionItems = buckets.get(key)
    if (sectionItems.length === 0) continue
    out.push({ key, label: priorityLabel(key), items: sectionItems })
  }
  return out
}
