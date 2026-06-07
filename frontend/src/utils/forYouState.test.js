import { describe, it, expect } from 'vitest'
import { addTargetFor } from './forYouState.js'

describe('addTargetFor', () => {
  it('routes a movie to the watchlist', () => {
    expect(addTargetFor({ media_type: 'movie', tmdb_id: 5 })).toEqual({ kind: 'watchlist' })
  })
  it('routes a show to its detail page', () => {
    expect(addTargetFor({ media_type: 'show', tmdb_id: 42 })).toEqual({ kind: 'detail', path: '/tv/42' })
  })
})
