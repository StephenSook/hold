import { describe, expect, it } from 'vitest'
import facts from '../../../docs/FACTS.json'
import board from './demo-board.json'
import { DEMO, payrollRemovedCents } from '@/state/demo'

/**
 * docs/FACTS.json is the authority for every headline number in this project: a real run writes
 * it and continuous integration recomputes it. The offline fixture the web app renders is written
 * by a different script, so these two can drift, and when they drifted once the interface
 * published $3,336.00 against the project's own $4,069.92.
 *
 * This test is the reason that cannot happen again. It fails on any disagreement, in either
 * direction, rather than trusting either file.
 */
const f = facts as unknown as {
  holding_before_cents: number
  holding_after_cents: number
  hold_days_before: number
  hold_days_after: number
  illegal_days_before: number
  illegal_days_after: number
  payroll_removed_cents: number
}

describe('the demo fixture agrees with FACTS.json', () => {
  it('on the cost of holding a performer', () => {
    expect(board.before.holding_cents).toBe(f.holding_before_cents)
    expect(board.after.result.pass2.holding_cents).toBe(f.holding_after_cents)
  })

  it('on the number of hold days, before and after', () => {
    expect(board.before.hold_days).toBe(f.hold_days_before)
    expect(board.after.result.pass2.hold_days).toBe(f.hold_days_after)
  })

  it('on the money the solved order removes', () => {
    expect(payrollRemovedCents).toBe(f.payroll_removed_cents)
  })

  it('on how many days cannot legally be shot', () => {
    const illegalBefore = board.before.verdicts.filter((v) => v.status === 'ILLEGAL').length
    const illegalAfter = board.after.result.pass1.filter(
      (v) => v.status === 'ILLEGAL' && (board.after.day_scene_ids as Record<string, string[]>)[String(v.day)]?.length,
    ).length
    expect(illegalBefore).toBe(f.illegal_days_before)
    expect(illegalAfter).toBe(f.illegal_days_after)
  })
})

describe('the fixture is honest about what it is', () => {
  it('is labelled constructed, so the interface can say so', () => {
    expect(DEMO.schedule.constructed).toBe(true)
  })

  it('names no real person: cast are single letters', () => {
    for (const member of DEMO.schedule.cast) {
      expect(member.letter).toMatch(/^[A-Z]$/)
    }
  })

  it('records the run that produced it', () => {
    expect(DEMO.runSha).toMatch(/^[0-9a-f]{7,40}$/)
    expect(DEMO.generatedAt).toMatch(/^\d{4}-\d{2}-\d{2}T/)
  })
})
