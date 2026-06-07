// Pure Calendar view-state transforms (no Vue, no DOM).
// Backend `items` arrive already sorted ascending by date.

// Format an ISO date (YYYY-MM-DD) to a "Weekday, Mon D" label. The explicit
// T00:00:00 keeps parsing in local time so the rendered day doesn't shift.
export function formatDayLabel(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr + 'T00:00:00').toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  })
}

// Group consecutive same-date items into ordered date buckets, preserving input
// order (no re-sort). Returns [] for null/undefined/empty input.
export function groupByDate(items) {
  if (!items || items.length === 0) return []
  const groups = []
  let current = null
  for (const item of items) {
    if (!current || current.date !== item.date) {
      current = { date: item.date, label: formatDayLabel(item.date), entries: [] }
      groups.push(current)
    }
    current.entries.push(item)
  }
  return groups
}
