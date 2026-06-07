import { describe, it, expect } from 'vitest'
import {
  parseWatchlistState,
  serializeWatchlistState,
  applyWatchlistView,
  groupWatchlistView,
  priorityLabel,
  parseTagsInput,
  formatTags,
} from './watchlistState.js'

const defaultState = {
  mediaType: 'all',
  status: 'all',
  sortBy: 'added',
  sortDir: 'desc',
  groupBy: 'none',
}

describe('parseWatchlistState', () => {
  it('returns the full default state for an empty query', () => {
    expect(parseWatchlistState({})).toEqual(defaultState)
  })

  it('is null-safe for undefined', () => {
    expect(parseWatchlistState(undefined)).toEqual(defaultState)
  })

  it('coerces a fully populated query', () => {
    expect(
      parseWatchlistState({ type: 'shows', status: 'pending', sort: 'rating', dir: 'asc' }),
    ).toEqual({ mediaType: 'shows', status: 'pending', sortBy: 'rating', sortDir: 'asc', groupBy: 'none' })
  })

  it('falls back to defaults for garbage values', () => {
    expect(
      parseWatchlistState({ type: 'x', status: 'bogus', sort: 'nope', dir: 'sideways' }),
    ).toEqual(defaultState)
  })
})

describe('serializeWatchlistState', () => {
  it('omits all defaults so a clean default state yields {}', () => {
    expect(serializeWatchlistState(parseWatchlistState({}))).toEqual({})
  })

  it('omits group when state lacks a groupBy field (no group=undefined)', () => {
    expect(
      serializeWatchlistState({
        mediaType: 'all',
        status: 'all',
        sortBy: 'added',
        sortDir: 'desc',
      }),
    ).toEqual({})
  })

  it('includes only the non-default keys as strings', () => {
    expect(
      serializeWatchlistState({
        mediaType: 'shows',
        status: 'pending',
        sortBy: 'rating',
        sortDir: 'asc',
        groupBy: 'none',
      }),
    ).toEqual({ type: 'shows', status: 'pending', sort: 'rating', dir: 'asc' })
  })
})

describe('round-trip', () => {
  it('serialize(parse(q)) deep-equals the populated query', () => {
    const q = { type: 'movies', status: 'downloading', sort: 'title', dir: 'asc' }
    expect(serializeWatchlistState(parseWatchlistState(q))).toEqual(q)
  })
})

describe('applyWatchlistView', () => {
  const mix = [
    {
      id: 1,
      media_type: 'movie',
      title: 'Banana',
      release_date: '2020-01-01',
      vote_average: 7.5,
      added_at: '2026-01-01T00:00:00Z',
      status: 'pending',
    },
    {
      id: 2,
      media_type: 'show',
      title: 'apple',
      release_date: '2021-06-01',
      vote_average: 9.1,
      added_at: '2026-02-01T00:00:00Z',
      status: 'added',
    },
    {
      id: 3,
      media_type: 'movie',
      title: 'Cherry',
      release_date: '2019-03-01',
      vote_average: 5.0,
      added_at: '2026-03-01T00:00:00Z',
      status: 'downloading',
    },
  ]

  it('filters by media type', () => {
    const movies = applyWatchlistView(mix, { ...defaultState, mediaType: 'movies' })
    expect(movies.map((i) => i.id).sort()).toEqual([1, 3])

    const shows = applyWatchlistView(mix, { ...defaultState, mediaType: 'shows' })
    expect(shows.map((i) => i.id)).toEqual([2])

    const all = applyWatchlistView(mix, { ...defaultState, mediaType: 'all' })
    expect(all.map((i) => i.id).sort()).toEqual([1, 2, 3])
  })

  it('filters by status', () => {
    const pending = applyWatchlistView(mix, { ...defaultState, status: 'pending' })
    expect(pending.map((i) => i.id)).toEqual([1])

    const all = applyWatchlistView(mix, { ...defaultState, status: 'all' })
    expect(all.map((i) => i.id).sort()).toEqual([1, 2, 3])
  })

  it('sorts by rating desc with nulls last', () => {
    const items = [
      { id: 1, media_type: 'movie', title: 'A', vote_average: 7.0, added_at: '2026-01-01T00:00:00Z', release_date: '2020-01-01', status: 'added' },
      { id: 2, media_type: 'movie', title: 'B', vote_average: null, added_at: '2026-01-02T00:00:00Z', release_date: '2020-01-02', status: 'added' },
      { id: 3, media_type: 'movie', title: 'C', vote_average: 9.0, added_at: '2026-01-03T00:00:00Z', release_date: '2020-01-03', status: 'added' },
    ]
    const out = applyWatchlistView(items, { ...defaultState, sortBy: 'rating', sortDir: 'desc' })
    expect(out.map((i) => i.id)).toEqual([3, 1, 2])
  })

  it('sorts by release desc with empty and null last', () => {
    const items = [
      { id: 1, media_type: 'movie', title: 'A', vote_average: 7.0, added_at: '2026-01-01T00:00:00Z', release_date: '2020-01-01', status: 'added' },
      { id: 2, media_type: 'movie', title: 'B', vote_average: 8.0, added_at: '2026-01-02T00:00:00Z', release_date: '', status: 'added' },
      { id: 3, media_type: 'movie', title: 'C', vote_average: 9.0, added_at: '2026-01-03T00:00:00Z', release_date: '2022-05-05', status: 'added' },
      { id: 4, media_type: 'movie', title: 'D', vote_average: 6.0, added_at: '2026-01-04T00:00:00Z', release_date: null, status: 'added' },
    ]
    const out = applyWatchlistView(items, { ...defaultState, sortBy: 'release', sortDir: 'desc' })
    // Direct, order-preserving assertion: present desc (3,1) then missing in ORIGINAL order (2,4).
    expect(out.map((i) => i.id)).toEqual([3, 1, 2, 4])
  })

  it('sorts by title asc case-insensitively', () => {
    const items = [
      { id: 1, media_type: 'movie', title: 'Banana', vote_average: 7.0, added_at: '2026-01-01T00:00:00Z', release_date: '2020-01-01', status: 'added' },
      { id: 2, media_type: 'movie', title: 'apple', vote_average: 8.0, added_at: '2026-01-02T00:00:00Z', release_date: '2020-01-02', status: 'added' },
      { id: 3, media_type: 'movie', title: 'Cherry', vote_average: 9.0, added_at: '2026-01-03T00:00:00Z', release_date: '2020-01-03', status: 'added' },
    ]
    const out = applyWatchlistView(items, { ...defaultState, sortBy: 'title', sortDir: 'asc' })
    expect(out.map((i) => i.title)).toEqual(['apple', 'Banana', 'Cherry'])
  })

  it('sorts by added desc (newest first)', () => {
    const items = [
      { id: 1, media_type: 'movie', title: 'A', vote_average: 7.0, added_at: '2026-01-01T00:00:00Z', release_date: '2020-01-01', status: 'added' },
      { id: 2, media_type: 'movie', title: 'B', vote_average: 8.0, added_at: '2026-03-01T00:00:00Z', release_date: '2020-01-02', status: 'added' },
      { id: 3, media_type: 'movie', title: 'C', vote_average: 9.0, added_at: '2026-02-01T00:00:00Z', release_date: '2020-01-03', status: 'added' },
    ]
    const out = applyWatchlistView(items, { ...defaultState, sortBy: 'added', sortDir: 'desc' })
    expect(out.map((i) => i.id)).toEqual([2, 3, 1])
  })

  it('does not mutate the input and returns a new array', () => {
    const input = [
      { id: 1, media_type: 'movie', title: 'B', vote_average: 7.0, added_at: '2026-01-01T00:00:00Z', release_date: '2020-01-01', status: 'added' },
      { id: 2, media_type: 'show', title: 'A', vote_average: 8.0, added_at: '2026-02-01T00:00:00Z', release_date: '2020-02-01', status: 'pending' },
    ]
    const before = input.slice()
    const result = applyWatchlistView(input, { ...defaultState, sortBy: 'title', sortDir: 'asc' })
    expect(input).toEqual(before)
    expect(result).not.toBe(input)
  })

  it('is stable for equal sort keys', () => {
    const items = [
      { id: 1, media_type: 'movie', title: 'Same', vote_average: 7.0, added_at: '2026-01-01T00:00:00Z', release_date: '2020-01-01', status: 'added' },
      { id: 2, media_type: 'movie', title: 'Same', vote_average: 7.0, added_at: '2026-01-01T00:00:00Z', release_date: '2020-01-01', status: 'added' },
      { id: 3, media_type: 'movie', title: 'Same', vote_average: 7.0, added_at: '2026-01-01T00:00:00Z', release_date: '2020-01-01', status: 'added' },
    ]
    const out = applyWatchlistView(items, { ...defaultState, sortBy: 'title', sortDir: 'asc' })
    expect(out.map((i) => i.id)).toEqual([1, 2, 3])
  })

  it('sorts by rating asc with nulls last (missing sorts last even ascending)', () => {
    const items = [
      { id: 1, media_type: 'movie', title: 'A', vote_average: 8.0, added_at: '2026-01-01T00:00:00Z', release_date: '2020-01-01', status: 'added' },
      { id: 2, media_type: 'movie', title: 'B', vote_average: null, added_at: '2026-01-02T00:00:00Z', release_date: '2020-01-02', status: 'added' },
      { id: 3, media_type: 'movie', title: 'C', vote_average: 3.0, added_at: '2026-01-03T00:00:00Z', release_date: '2020-01-03', status: 'added' },
    ]
    const out = applyWatchlistView(items, { ...defaultState, sortBy: 'rating', sortDir: 'asc' })
    // present items ascending (3.0 then 8.0), null last
    expect(out.map((i) => i.id)).toEqual([3, 1, 2])
  })

  it('sorts by release asc with empty last (missing sorts last even ascending)', () => {
    const items = [
      { id: 1, media_type: 'movie', title: 'A', vote_average: 7.0, added_at: '2026-01-01T00:00:00Z', release_date: '2020-01-01', status: 'added' },
      { id: 2, media_type: 'movie', title: 'B', vote_average: 8.0, added_at: '2026-01-02T00:00:00Z', release_date: '', status: 'added' },
      { id: 3, media_type: 'movie', title: 'C', vote_average: 9.0, added_at: '2026-01-03T00:00:00Z', release_date: '2000-01-01', status: 'added' },
    ]
    const out = applyWatchlistView(items, { ...defaultState, sortBy: 'release', sortDir: 'asc' })
    // present dates ascending ('2000-01-01' then '2020-01-01'), '' last
    expect(out.map((i) => i.id)).toEqual([3, 1, 2])
  })

  it('treats vote_average 0 as a real rating (not missing) in both directions', () => {
    const items = [
      { id: 1, media_type: 'movie', title: 'Zero', vote_average: 0, added_at: '2026-01-01T00:00:00Z', release_date: '2020-01-01', status: 'added' },
      { id: 2, media_type: 'movie', title: 'Mid', vote_average: 5.0, added_at: '2026-01-02T00:00:00Z', release_date: '2020-01-02', status: 'added' },
      { id: 3, media_type: 'movie', title: 'Null', vote_average: null, added_at: '2026-01-03T00:00:00Z', release_date: '2020-01-03', status: 'added' },
      { id: 4, media_type: 'movie', title: 'High', vote_average: 8.0, added_at: '2026-01-04T00:00:00Z', release_date: '2020-01-04', status: 'added' },
    ]
    // desc: present descending (8, 5, 0) then null last; the 0 item sorts ABOVE the null item.
    const desc = applyWatchlistView(items, { ...defaultState, sortBy: 'rating', sortDir: 'desc' })
    expect(desc.map((i) => i.id)).toEqual([4, 2, 1, 3])

    // asc: the 0 item is FIRST among present (lowest real rating), null still LAST.
    const asc = applyWatchlistView(items, { ...defaultState, sortBy: 'rating', sortDir: 'asc' })
    expect(asc.map((i) => i.id)).toEqual([1, 2, 4, 3])
  })

  it('treats an early release_date (0001-01-01) as a real value, not missing', () => {
    const items = [
      { id: 1, media_type: 'movie', title: 'Ancient', vote_average: 7.0, added_at: '2026-01-01T00:00:00Z', release_date: '0001-01-01', status: 'added' },
      { id: 2, media_type: 'movie', title: 'Modern', vote_average: 8.0, added_at: '2026-01-02T00:00:00Z', release_date: '2010-05-05', status: 'added' },
      { id: 3, media_type: 'movie', title: 'Old', vote_average: 9.0, added_at: '2026-01-03T00:00:00Z', release_date: '1999-12-31', status: 'added' },
      { id: 4, media_type: 'movie', title: 'NoDate', vote_average: 6.0, added_at: '2026-01-04T00:00:00Z', release_date: null, status: 'added' },
    ]
    const out = applyWatchlistView(items, { ...defaultState, sortBy: 'release', sortDir: 'asc' })
    // '0001-01-01' is the oldest real date -> FIRST; null is missing -> LAST.
    expect(out.map((i) => i.id)).toEqual([1, 3, 2, 4])
  })

  it('preserves original order among multiple missing keys (direct stability assertion)', () => {
    const items = [
      { id: 'a', media_type: 'movie', title: 'A', vote_average: null, added_at: '2026-01-01T00:00:00Z', release_date: '2020-01-01', status: 'added' },
      { id: 'b', media_type: 'movie', title: 'B', vote_average: 5.0, added_at: '2026-01-02T00:00:00Z', release_date: '2020-01-02', status: 'added' },
      { id: 'c', media_type: 'movie', title: 'C', vote_average: null, added_at: '2026-01-03T00:00:00Z', release_date: '2020-01-03', status: 'added' },
      { id: 'd', media_type: 'movie', title: 'D', vote_average: 8.0, added_at: '2026-01-04T00:00:00Z', release_date: '2020-01-04', status: 'added' },
    ]
    const out = applyWatchlistView(items, { ...defaultState, sortBy: 'rating', sortDir: 'desc' })
    // present items first by rating (d=8, b=5), then missing 'a','c' in ORIGINAL relative order.
    // Direct array comparison (NOT order-agnostic) to catch a stability regression.
    expect(out.map((i) => i.id)).toEqual(['d', 'b', 'a', 'c'])
  })
})

describe('groupBy state', () => {
  it('parses group=priority', () => {
    expect(parseWatchlistState({ group: 'priority' }).groupBy).toBe('priority')
  })

  it('defaults groupBy to none and omits it from serialize', () => {
    expect(parseWatchlistState({}).groupBy).toBe('none')
    expect(serializeWatchlistState(parseWatchlistState({}))).toEqual({})
  })

  it('serializes a non-default groupBy to group', () => {
    expect(serializeWatchlistState(parseWatchlistState({ group: 'priority' }))).toEqual({
      group: 'priority',
    })
  })

  it('falls back to none for a garbage group', () => {
    expect(parseWatchlistState({ group: 'bogus' }).groupBy).toBe('none')
  })
})

describe('priorityLabel', () => {
  it('maps known priorities to labels', () => {
    expect(priorityLabel(1)).toBe('High')
    expect(priorityLabel(0)).toBe('Normal')
    expect(priorityLabel(-1)).toBe('Low')
  })

  it('falls back to Normal for unknown priorities', () => {
    expect(priorityLabel(5)).toBe('Normal')
  })
})

describe('parseTagsInput / formatTags', () => {
  it('splits, trims, drops empties, and dedupes preserving first-seen order', () => {
    expect(parseTagsInput('a, b ,a, ,c')).toEqual(['a', 'b', 'c'])
  })

  it('returns an empty array for an empty string', () => {
    expect(parseTagsInput('')).toEqual([])
  })

  it('formats tags back to a comma-separated string', () => {
    expect(formatTags(['a', 'b'])).toBe('a, b')
  })
})

describe('groupWatchlistView', () => {
  const items = [
    { id: 1, media_type: 'movie', priority: 1, vote_average: 5, status: 'pending', added_at: '2026-01-01T00:00:00Z' },
    { id: 2, media_type: 'movie', priority: 0, vote_average: 9, status: 'pending', added_at: '2026-02-01T00:00:00Z' },
    { id: 3, media_type: 'movie', priority: -1, vote_average: 7, status: 'pending', added_at: '2026-03-01T00:00:00Z' },
    { id: 4, media_type: 'show', priority: 1, vote_average: 8, status: 'added', added_at: '2026-04-01T00:00:00Z' },
    { id: 5, media_type: 'movie', vote_average: 6, status: 'pending', added_at: '2026-05-01T00:00:00Z' },
  ]

  it('buckets into High -> Normal -> Low order with labels', () => {
    const sections = groupWatchlistView(items, defaultState)
    expect(sections.map((s) => [s.key, s.label])).toEqual([
      [1, 'High'],
      [0, 'Normal'],
      [-1, 'Low'],
    ])
  })

  it('places items without a priority in the Normal (0) section', () => {
    const sections = groupWatchlistView(items, defaultState)
    const normal = sections.find((s) => s.key === 0)
    expect(normal.items.map((i) => i.id)).toContain(5)
  })

  it('preserves the active sort within each section', () => {
    const sections = groupWatchlistView(items, { ...defaultState, sortBy: 'rating', sortDir: 'asc' })
    const byKey = Object.fromEntries(sections.map((s) => [s.key, s.items.map((i) => i.id)]))
    expect(byKey[1]).toEqual([1, 4])
    expect(byKey[0]).toEqual([5, 2])
    expect(byKey[-1]).toEqual([3])
  })

  it('applies the active media filter within each section', () => {
    const sections = groupWatchlistView(items, { ...defaultState, mediaType: 'movies' })
    const high = sections.find((s) => s.key === 1)
    expect(high.items.map((i) => i.id)).toEqual([1])
  })

  it('omits empty sections after filtering', () => {
    const sections = groupWatchlistView(items, { ...defaultState, status: 'added' })
    expect(sections.map((s) => s.key)).toEqual([1])
    expect(sections[0].items.map((i) => i.id)).toEqual([4])
  })
})
