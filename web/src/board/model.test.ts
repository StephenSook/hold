import { describe, expect, it } from 'vitest'
import board from '@/fixtures/demo-board.json'
import type { ScheduleInput, Verdict } from '@/types/contracts'
import { buildRows, dayMapOf, moveStrip, orderOf, reindexDays, unscheduled, withTotals } from './model'

const schedule = board.schedule as unknown as ScheduleInput
const beforeMap = board.before.day_scene_ids as Record<string, string[]>
const verdicts = board.before.verdicts as unknown as Verdict[]

describe('buildRows', () => {
  it('gives every shooting day a break, including the empty ones', () => {
    const rows = buildRows(schedule, beforeMap, verdicts)
    const breaks = rows.filter((r) => r.kind === 'break')
    expect(breaks).toHaveLength(schedule.days.length)
    expect(breaks.map((b) => b.day)).toEqual(schedule.days.map((_, i) => i))
  })

  it('places every scene the day map names, once', () => {
    const rows = buildRows(schedule, beforeMap, verdicts)
    const ids = orderOf(rows)
    expect(ids).toHaveLength(schedule.scenes.length)
    expect(new Set(ids).size).toBe(ids.length)
  })

  it('totals the page eighths a day carries', () => {
    const rows = buildRows(schedule, beforeMap, verdicts)
    const byId = new Map(schedule.scenes.map((s) => [s.id, s]))
    for (const row of rows) {
      if (row.kind !== 'break') continue
      const expected = row.sceneIds.reduce((sum, id) => sum + (byId.get(id)?.pages_eighths ?? 0), 0)
      expect(row.pagesEighths).toBe(expected)
    }
  })

  it('hands the illegal day its verdict', () => {
    const rows = buildRows(schedule, beforeMap, verdicts)
    const illegal = rows.filter((r) => r.kind === 'break' && r.verdict?.status === 'ILLEGAL')
    expect(illegal).toHaveLength(1)
    expect(illegal[0].kind === 'break' && illegal[0].verdict?.violations.length).toBeGreaterThan(0)
  })
})

describe('dayMapOf', () => {
  it('round-trips the map it was built from', () => {
    const rows = buildRows(schedule, beforeMap, verdicts)
    expect(dayMapOf(rows, schedule.days.length)).toEqual(beforeMap)
  })
})

describe('moving a strip', () => {
  it('onto a strip in the next day joins that day', () => {
    const rows = buildRows(schedule, beforeMap, verdicts)
    // s1 is alone on day 0 and s9 is alone on day 1. Dropping s1 onto s9 takes s9's place,
    // which is between the day-0 break and the day-1 break, so s1 is now a day-1 scene.
    const moved = reindexDays(moveStrip(rows, 's1', 's9'), schedule.days.length)
    const map = dayMapOf(moved, schedule.days.length)
    expect(map['0']).toEqual([])
    expect(map['1']).toEqual(['s9', 's1'])
  })

  it('onto a day break lands past it, in the day that break opens', () => {
    // Removing the strip shifts everything above the target up by one, so the strip settles
    // after the break it was dropped on. Dropping on the day-1 break therefore means day 2.
    // A test that asserted day 1 here would be asserting a different drop model.
    const rows = buildRows(schedule, beforeMap, verdicts)
    const moved = reindexDays(moveStrip(rows, 's1', 'break:1'), schedule.days.length)
    const map = dayMapOf(moved, schedule.days.length)
    expect(map['0']).toEqual([])
    expect(map['1']).toEqual(['s9'])
    expect(map['2']).toEqual(['s1', 's7'])
  })

  it('leaves the breaks where they are', () => {
    const rows = buildRows(schedule, beforeMap, verdicts)
    const moved = moveStrip(rows, 's1', 'break:3')
    const breaks = moved.filter((r) => r.kind === 'break').map((r) => r.day)
    expect(breaks).toEqual([...breaks].sort((a, b) => a - b))
  })

  it('refuses to move a break', () => {
    const rows = buildRows(schedule, beforeMap, verdicts)
    expect(moveStrip(rows, 'break:0', 's5')).toBe(rows)
  })

  it('recounts the page total after the move rather than carrying it', () => {
    const rows = buildRows(schedule, beforeMap, verdicts)
    const before = rows.find((r) => r.kind === 'break' && r.day === 0)
    const moved = withTotals(reindexDays(moveStrip(rows, 's1', 'break:1'), schedule.days.length), schedule)
    const after = moved.find((r) => r.kind === 'break' && r.day === 0)
    expect(before?.kind === 'break' && before.pagesEighths).toBeGreaterThan(0)
    expect(after?.kind === 'break' && after.pagesEighths).toBe(0)
  })
})

describe('unscheduled', () => {
  it('is empty when every scene is placed', () => {
    expect(unscheduled(schedule, beforeMap)).toEqual([])
  })

  it('holds a scene no day names', () => {
    const partial = { ...beforeMap, '0': [] }
    expect(unscheduled(schedule, partial).map((s) => s.id)).toEqual(['s1'])
  })
})
