import { describe, it, expect } from 'vitest'
import { groupByDate, formatDayLabel } from './calendarState.js'

describe('groupByDate', () => {
  it('buckets two entries sharing a date into one group', () => {
    const items = [
      { date: '2026-06-10', title: 'A' },
      { date: '2026-06-10', title: 'B' },
    ]
    const groups = groupByDate(items)
    expect(groups).toHaveLength(1)
    expect(groups[0].date).toBe('2026-06-10')
    expect(groups[0].label).toBe(formatDayLabel('2026-06-10'))
    expect(groups[0].entries).toHaveLength(2)
    expect(groups[0].entries.map((e) => e.title)).toEqual(['A', 'B'])
  })

  it('keeps two different dates as two groups in ascending order', () => {
    const items = [
      { date: '2026-06-10', title: 'A' },
      { date: '2026-06-11', title: 'B' },
      { date: '2026-06-11', title: 'C' },
    ]
    const groups = groupByDate(items)
    expect(groups).toHaveLength(2)
    expect(groups[0].date < groups[1].date).toBe(true)
    expect(groups[0].entries).toHaveLength(1)
    expect(groups[1].entries).toHaveLength(2)
  })

  it('is null-safe', () => {
    expect(groupByDate([])).toEqual([])
    expect(groupByDate(null)).toEqual([])
    expect(groupByDate(undefined)).toEqual([])
  })

  it('keeps non-adjacent equal dates as separate buckets in input order', () => {
    const items = [
      { date: '2026-06-10', title: 'A' },
      { date: '2026-06-11', title: 'B' },
      { date: '2026-06-10', title: 'C' },
    ]
    const groups = groupByDate(items)
    expect(groups.map((g) => g.date)).toEqual(['2026-06-10', '2026-06-11', '2026-06-10'])
    expect(groups).toHaveLength(3)
    expect(groups[0].entries).toHaveLength(1)
    expect(groups[0].entries[0].title).toBe('A')
    expect(groups[2].entries[0].title).toBe('C')
  })
})

describe('formatDayLabel', () => {
  it('formats an ISO date to a Weekday, Mon D label', () => {
    expect(formatDayLabel('2026-06-10')).toBe('Wed, Jun 10')
  })

  it('is null-safe', () => {
    expect(formatDayLabel('')).toBe('')
    expect(formatDayLabel(null)).toBe('')
  })
})
