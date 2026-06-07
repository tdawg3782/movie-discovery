import { describe, it, expect } from 'vitest'
import { parseDiscoverState, serializeDiscoverState, clampPage } from './discoverState.js'

const defaultState = {
  tab: 'movies',
  page: 1,
  search: '',
  filters: {
    genre: null,
    yearGte: null,
    yearLte: null,
    ratingGte: null,
    certification: null,
    sortBy: 'popularity.desc',
    inLibrary: false,
    notInLibrary: false,
  },
}

describe('parseDiscoverState', () => {
  it('returns the full default state for an empty query', () => {
    expect(parseDiscoverState({})).toEqual(defaultState)
  })

  it('coerces types for a populated query', () => {
    const state = parseDiscoverState({
      page: '5',
      tab: 'shows',
      q: 'matrix',
      genre: '28,12',
      ratingGte: '8',
      inLibrary: 'true',
    })
    expect(state.tab).toBe('shows')
    expect(state.page).toBe(5)
    expect(state.search).toBe('matrix')
    expect(state.filters.genre).toBe('28,12')
    expect(state.filters.ratingGte).toBe(8)
    expect(state.filters.inLibrary).toBe(true)
    // remaining filters at defaults
    expect(state.filters.yearGte).toBeNull()
    expect(state.filters.yearLte).toBeNull()
    expect(state.filters.certification).toBeNull()
    expect(state.filters.sortBy).toBe('popularity.desc')
    expect(state.filters.notInLibrary).toBe(false)
  })

  it('defaults page to 1 for invalid or sub-1 values', () => {
    expect(parseDiscoverState({ page: 'abc' }).page).toBe(1)
    expect(parseDiscoverState({ page: '0' }).page).toBe(1)
    expect(parseDiscoverState({ page: '-3' }).page).toBe(1)
  })

  it('defaults page to 1 for partially-numeric or non-clean integer strings', () => {
    expect(parseDiscoverState({ page: '2abc' }).page).toBe(1)
    expect(parseDiscoverState({ page: '1.5' }).page).toBe(1)
    expect(parseDiscoverState({ page: '0' }).page).toBe(1)
    expect(parseDiscoverState({ page: '-1' }).page).toBe(1)
    expect(parseDiscoverState({ page: '' }).page).toBe(1)
    expect(parseDiscoverState({ page: 'abc' }).page).toBe(1)
    expect(parseDiscoverState({ page: ' 3' }).page).toBe(1)
    expect(parseDiscoverState({}).page).toBe(1)
  })

  it('accepts clean positive integer page strings', () => {
    expect(parseDiscoverState({ page: '5' }).page).toBe(5)
    expect(parseDiscoverState({ page: '1' }).page).toBe(1)
  })
})

describe('serializeDiscoverState', () => {
  it('omits all defaults so a clean default state yields {}', () => {
    expect(serializeDiscoverState(parseDiscoverState({}))).toEqual({})
  })

  it('includes only the non-default keys as strings', () => {
    const state = {
      tab: 'shows',
      page: 5,
      search: 'matrix',
      filters: {
        genre: '28,12',
        yearGte: 2000,
        yearLte: 2020,
        ratingGte: 8,
        certification: 'PG-13',
        sortBy: 'vote_average.desc',
        inLibrary: true,
        notInLibrary: true,
      },
    }
    expect(serializeDiscoverState(state)).toEqual({
      tab: 'shows',
      page: '5',
      q: 'matrix',
      genre: '28,12',
      yearGte: '2000',
      yearLte: '2020',
      ratingGte: '8',
      certification: 'PG-13',
      sortBy: 'vote_average.desc',
      inLibrary: 'true',
      notInLibrary: 'true',
    })
  })
})

describe('round-trip', () => {
  it('serialize(parse(q)) deep-equals the populated query', () => {
    const q = {
      page: '5',
      tab: 'shows',
      q: 'matrix',
      genre: '28,12',
      ratingGte: '8',
      inLibrary: 'true',
    }
    expect(serializeDiscoverState(parseDiscoverState(q))).toEqual(q)
  })
})

describe('clampPage', () => {
  it('clamps to the [1, totalPages] range', () => {
    expect(clampPage(0, 10)).toBe(1)
    expect(clampPage(99, 10)).toBe(10)
    expect(clampPage(3, 10)).toBe(3)
    expect(clampPage(1, 0)).toBe(1)
  })
})
