/**
 * The board as a flat list, which is what a physical board is.
 *
 * A strip board is strips in one running order with a day break slotted in where a shooting
 * day ends. Membership of a day is not a property of the strip: it is where the strip sits
 * relative to the breaks. Slide a strip past a break and it belongs to the next day. Every
 * rule in this file follows from that one fact, which is why day membership is always derived
 * and never stored twice.
 */
import type { ScheduleInput, Scene, Verdict } from '@/types/contracts'

export type DayMap = Record<string, string[]>

export interface StripRow {
  kind: 'strip'
  id: string
  scene: Scene
  day: number
}

export interface BreakRow {
  kind: 'break'
  id: string
  day: number
  /** Scenes scheduled into this day. */
  sceneIds: string[]
  pagesEighths: number
  verdict: Verdict | null
}

export type BoardRow = StripRow | BreakRow

export const breakId = (day: number): string => `break:${day}`

/** The scene ids in board order, ignoring the breaks. */
export function orderOf(rows: BoardRow[]): string[] {
  return rows.filter((r): r is StripRow => r.kind === 'strip').map((r) => r.id)
}

/** The day map a set of rows describes, including days that hold nothing. */
export function dayMapOf(rows: BoardRow[], dayCount: number): DayMap {
  const map: DayMap = {}
  for (let d = 0; d < dayCount; d += 1) map[String(d)] = []
  let day = 0
  for (const row of rows) {
    if (row.kind === 'break') {
      day = Math.min(row.day + 1, dayCount - 1)
      continue
    }
    map[String(Math.min(day, dayCount - 1))].push(row.id)
  }
  return map
}

/**
 * Build the board. Every shooting day gets a break, including an empty one, because an empty
 * day is a place a strip can be dropped and an assistant director needs to see it there.
 */
export function buildRows(schedule: ScheduleInput, dayMap: DayMap, verdicts: Verdict[]): BoardRow[] {
  const byId = new Map(schedule.scenes.map((s) => [s.id, s]))
  const verdictFor = new Map(verdicts.map((v) => [v.day, v]))
  const rows: BoardRow[] = []

  for (let day = 0; day < schedule.days.length; day += 1) {
    const sceneIds = (dayMap[String(day)] ?? []).filter((id) => byId.has(id))
    for (const id of sceneIds) {
      rows.push({ kind: 'strip', id, scene: byId.get(id)!, day })
    }
    rows.push({
      kind: 'break',
      id: breakId(day),
      day,
      sceneIds,
      pagesEighths: sceneIds.reduce((sum, id) => sum + (byId.get(id)?.pages_eighths ?? 0), 0),
      verdict: verdictFor.get(day) ?? null,
    })
  }
  return rows
}

/** Move one strip to a new index in the flat list. Breaks never move. */
export function moveStrip(rows: BoardRow[], activeId: string, overId: string): BoardRow[] {
  const from = rows.findIndex((r) => r.id === activeId)
  const to = rows.findIndex((r) => r.id === overId)
  if (from < 0 || to < 0 || from === to) return rows
  if (rows[from].kind !== 'strip') return rows
  const next = rows.slice()
  const [moved] = next.splice(from, 1)
  next.splice(to, 0, moved)
  return next
}

/** Reassign each strip's day after a move, so the row carries what its position now means. */
export function reindexDays(rows: BoardRow[], dayCount: number): BoardRow[] {
  const map = dayMapOf(rows, dayCount)
  const dayOf = new Map<string, number>()
  for (const [day, ids] of Object.entries(map)) for (const id of ids) dayOf.set(id, Number(day))
  return rows.map((row) =>
    row.kind === 'strip'
      ? { ...row, day: dayOf.get(row.id) ?? row.day }
      : { ...row, sceneIds: map[String(row.day)] ?? [] },
  )
}

/**
 * The day totals a break prints. Recomputed from the rows, never carried, so a drag cannot
 * leave a stale page count on screen.
 */
export function withTotals(rows: BoardRow[], schedule: ScheduleInput): BoardRow[] {
  const byId = new Map(schedule.scenes.map((s) => [s.id, s]))
  return rows.map((row) =>
    row.kind === 'break'
      ? {
          ...row,
          pagesEighths: row.sceneIds.reduce((sum, id) => sum + (byId.get(id)?.pages_eighths ?? 0), 0),
        }
      : row,
  )
}

/** Scenes on the board, in board order, that are not in any day: the unscheduled area. */
export function unscheduled(schedule: ScheduleInput, dayMap: DayMap): Scene[] {
  const placed = new Set(Object.values(dayMap).flat())
  return schedule.scenes.filter((s) => !placed.has(s.id))
}
