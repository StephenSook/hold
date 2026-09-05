import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Play, RotateCcw, TriangleAlert } from 'lucide-react'
import { Stripboard } from '@/board/Stripboard'
import { StripLegend } from '@/board/StripLegend'
import { buildRows, withTotals, type BoardRow } from '@/board/model'
import { VerdictDialog } from '@/verdict/VerdictDialog'
import { ActionButton } from '@/components/Action'
import { Figure } from '@/components/Figure'
import { DEMO, payrollRemovedCents } from '@/state/demo'
import { useSolve } from '@/state/useSolve'
import { dollars, shootDate } from '@/lib/format'
import type { Verdict } from '@/types/contracts'

/**
 * The working board.
 *
 * Drag a strip past a day break and it belongs to the next day, exactly as on a physical board.
 * Solve sends the schedule to the API and lays the answer out; when the API cannot be reached the
 * board falls back to the recorded run and says so on screen rather than pretending.
 */
export function BoardPage() {
  const solver = useSolve()
  const [openDay, setOpenDay] = useState<number | null>(null)
  const [orderVersion, setOrderVersion] = useState(0)
  const [usedFallback, setUsedFallback] = useState(false)

  const beforeRows = useMemo(
    () => withTotals(buildRows(DEMO.schedule, DEMO.before.dayMap, DEMO.before.verdicts), DEMO.schedule),
    [],
  )
  const [rows, setRows] = useState<BoardRow[]>(beforeRows)

  const verdicts: Verdict[] = useMemo(() => {
    const source = rows.map((row) => (row.kind === 'break' ? row.verdict : null)).filter(Boolean) as Verdict[]
    return source
  }, [rows])

  const onRowsChange = useCallback((next: BoardRow[]) => {
    setRows(next)
    setOrderVersion((v) => v + 1)
  }, [])

  const applySolved = useCallback((dayMap: Record<string, string[]>, pass1: Verdict[]) => {
    setRows(withTotals(buildRows(DEMO.schedule, dayMap, pass1), DEMO.schedule))
    setOrderVersion((v) => v + 1)
  }, [])

  // The solver is given the schedule, not the current arrangement of it: the day assignment is
  // what pass 2 decides, so sending our arrangement would be asking it to confirm our answer.
  // What is on screen stays on screen, with its own verdicts, until a solved order arrives.
  const onSolve = useCallback(async () => {
    setUsedFallback(false)
    await solver.solve(DEMO.schedule)
  }, [solver])

  // Lay the answer out when one arrives, once per job. This was written as a bare call during
  // render, which sets state while React is rendering and is only safe by accident; keying an
  // effect on the job id makes "once per solve" the actual mechanism rather than a guard.
  const laidOut = useRef<string | null>(null)
  useEffect(() => {
    if (solver.phase !== 'done' || !solver.result || !solver.dayMap) return
    if (laidOut.current === solver.jobId) return
    laidOut.current = solver.jobId
    applySolved(solver.dayMap, solver.result.pass1)
  }, [solver.phase, solver.result, solver.dayMap, solver.jobId, applySolved])

  const onFallback = useCallback(() => {
    applySolved(DEMO.after.dayMap, DEMO.after.result.pass1)
    setUsedFallback(true)
  }, [applySolved])

  const onReset = useCallback(() => {
    setRows(beforeRows)
    setOrderVersion(0)
    laidOut.current = null
    solver.reset()
    setUsedFallback(false)
  }, [beforeRows, solver])

  const solvedPass2 = solver.result?.pass2 ?? (usedFallback ? DEMO.after.result.pass2 : null)
  const openVerdict = openDay === null ? null : (verdicts.find((v) => v.day === openDay) ?? null)

  return (
    <div className="mx-auto max-w-[1440px] px-5 py-10 sm:px-8 sm:py-14">
      <div className="flex flex-wrap items-end justify-between gap-6">
        <div>
          <p className="script-label text-11 text-bone-faint">Stripboard</p>
          <h1 className="display-wide mt-3 text-28 text-bone sm:text-36">The board</h1>
          <p className="mt-3 max-w-[58ch] text-14 text-bone-dim">
            Drag a strip past a day break and it moves to that day. Lift with the space bar, move
            with the arrow keys, drop with space.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <ActionButton
            onClick={onSolve}
            disabled={solver.phase === 'solving'}
            icon={<Play className="size-3.5" />}
          >
            {solver.phase === 'solving' ? 'Solving' : 'Solve'}
          </ActionButton>
          <ActionButton onClick={onReset} variant="quiet" icon={<RotateCcw className="size-3.5" />}>
            Reset
          </ActionButton>
        </div>
      </div>

      {solver.phase === 'failed' && (
        <div
          role="status"
          className="script mt-6 flex flex-wrap items-center gap-x-4 gap-y-2 border border-flag/60 px-4 py-3 text-12 text-bone"
        >
          <TriangleAlert className="size-4 text-flag" aria-hidden="true" />
          <span>The solve did not run: {solver.error}.</span>
          <button
            type="button"
            onClick={onFallback}
            className="cursor-pointer underline decoration-rail underline-offset-4 transition-colors hover:decoration-bone"
          >
            Show the recorded run instead
          </button>
        </div>
      )}

      {usedFallback && (
        <p className="script mt-6 border border-rail px-4 py-3 text-12 text-bone-dim">
          This is the run recorded on {DEMO.generatedAt.slice(0, 10)} at commit {DEMO.runSha}, not a
          live solve.
        </p>
      )}

      <dl className="mt-8 flex flex-wrap gap-x-12 gap-y-6">
        <Figure
          label="Hold days"
          from={String(DEMO.before.holdDays)}
          to={solvedPass2 ? String(solvedPass2.hold_days) : String(DEMO.before.holdDays)}
        />
        <Figure
          label="Payroll removed"
          value={solvedPass2 ? dollars(DEMO.before.holdingCents - solvedPass2.holding_cents) : 'not solved'}
        />
        <Figure
          label="Pass 2"
          value={solvedPass2?.status ?? 'not run'}
          source={solvedPass2 ? `bound ${dollars(solvedPass2.bound)}` : undefined}
        />
        {solver.solveMs !== null && <Figure label="Solve" value={`${Math.round(solver.solveMs)} ms`} />}
      </dl>

      <div className="mt-8 overflow-hidden border border-rail">
        <Stripboard
          schedule={DEMO.schedule}
          rows={rows}
          onRowsChange={onRowsChange}
          onOpenVerdict={setOpenDay}
          orderVersion={orderVersion}
        />
      </div>

      <div className="mt-5">
        <StripLegend />
      </div>

      <VerdictDialog
        verdict={openVerdict}
        date={openVerdict ? shootDate(DEMO.schedule.days[openVerdict.day].date) : undefined}
        onClose={() => setOpenDay(null)}
      />

      <p className="script mt-10 text-11 text-bone-faint">
        Constructed demo data. Cast are letters, not names. The rule side is real. Removing the four
        hold days is worth {dollars(payrollRemovedCents)} at the published low-budget day rate.
      </p>
    </div>
  )
}
