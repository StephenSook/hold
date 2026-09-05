import demoBoard from '@/fixtures/demo-board.json'
import type { ScheduleInput, SolveResult, Verdict } from '@/types/contracts'
import type { DayMap } from '@/board/model'

/**
 * The demo, as a real run recorded it.
 *
 * web/scripts/capture_demo_board.py writes this file by running the repository's own solver and
 * checker over the committed demo schedule, so every figure the interface shows offline came out
 * of the engine. The live API is still the source of truth whenever it answers; this is what the
 * first paint, a component test and an offline day view read.
 */
export interface DemoBoard {
  generatedAt: string
  runSha: string
  schedule: ScheduleInput
  before: { dayMap: DayMap; holdDays: number; holdingCents: number; verdicts: Verdict[] }
  after: { dayMap: DayMap; result: SolveResult }
}

const raw = demoBoard as unknown as {
  _generated_at: string
  _run_sha: string
  schedule: ScheduleInput
  before: { day_scene_ids: DayMap; hold_days: number; holding_cents: number; verdicts: Verdict[] }
  after: { day_scene_ids: DayMap; result: SolveResult }
}

export const DEMO: DemoBoard = {
  generatedAt: raw._generated_at,
  runSha: raw._run_sha,
  schedule: raw.schedule,
  before: {
    dayMap: raw.before.day_scene_ids,
    holdDays: raw.before.hold_days,
    holdingCents: raw.before.holding_cents,
    verdicts: raw.before.verdicts,
  },
  after: { dayMap: raw.after.day_scene_ids, result: raw.after.result },
}

/** The days the before plan cannot legally shoot. */
export const illegalDaysBefore = DEMO.before.verdicts.filter((v) => v.status === 'ILLEGAL')

/** Money the solved order removes from payroll, in cents. */
export const payrollRemovedCents = DEMO.before.holdingCents - DEMO.after.result.pass2.holding_cents
