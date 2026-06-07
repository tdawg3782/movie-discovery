// Where a recommendation card's "add" action should go: movies add straight to the
// watchlist; shows must pick seasons, so route to the detail page instead.
export function addTargetFor(media) {
  if (media.media_type === 'movie') return { kind: 'watchlist' }
  return { kind: 'detail', path: `/tv/${media.tmdb_id}` }
}
