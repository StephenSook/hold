import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Play, RotateCcw, TriangleAlert } from 'lucide-react'
import { Stripboard } from '@/board/Stripboard'
import { StripLegend } from '@/board/StripLegend'
import { SetEvents } from '@/board/SetEvents'
import { AskAgent } from '@/board/AskAgent'
import { buildRows, withTotals, type BoardRow } from '@/board/model'
import { VerdictDialog } from '@/verdict/VerdictDialog'
import { ActionButton } from '@/components/Action'
import { Figure } from '@/components/Figure'
import { DEMO, payrollRemovedCents } from '@/state/demo'
import { clearImported, getImported } from '@/state/handoff'
import { useSolve } from '@/state/useSolve'
import { useSetEvent } from '@/state/useSetEvent'
import { useEventStream } from '@/state/useEventStream'
import { dollars, shootDate } from '@/lib/format'
import type { ScheduleInput, SetEventKind, Verdict } from '@/types/contracts'

/**
 * The working board.
 *
 * Drag a strip past a day break and it belongs to the next day, exactly as on a physical board.
 * Solve sends the schedule to the API and lays the answer out; when the API cannot be reached the
 * board offers the recorded run and says which it is showing rather than substituting quietly.
 */
export function BoardPage() {
  const solver = useSolve()
  const setEvent = useSetEvent()
  const [openDay, setOpenDay] = useState<number | null>(null)
  const [orderVersion, setOrderVersion] = useState(0)
  const [usedFallback, setUsedFallback] = useState(false)
  // A schedule the import page read from a document, if there is one. Held in state rather than
  // read on every render: the board owns it from here, and reset has to be able to put it down.
  // As a memo it could not, and the banner outlived the schedule it described until a remount.
  const [imported, setImported] = useState<ScheduleInput | null>(() => getImported())
  const [schedule, setSchedule] = useState<ScheduleInput>(imported ?? DEMO.schedule)
  const [transport, setTransport] = useState<string | null>(null)

  /**
   * The starting arrangement.
   *
   * The demo has a hand-built plan to improve on, which is the whole before-and-after. An imported
   * document does not: a scene record carries no day, so nothing here knows which day a scene was
   * meant for, and inventing an arrangement would be inventing the very thing the solver decides.
   * So an imported board starts with its days empty and solves immediately, which is what the
   * confirm button has always said it does.
   */
  const beforeRows = useMemo(
    () =>
      imported
        ? withTotals(buildRows(imported, {}, []), imported)
        : withTotals(buildRows(DEMO.schedule, DEMO.before.dayMap, DEMO.before.verdicts), DEMO.schedule),
    [imported],
  )
  const [rows, setRows] = useState<BoardRow[]>(beforeRows)

  const stream = useEventStream(solver.jobId, solver.jobId !== null)

  const verdicts: Verdict[] = useMemo(
    () => rows.flatMap((row) => (row.kind === 'break' && row.verdict ? [row.verdict] : [])),
    [rows],
  )

  const onRowsChange = useCallback((next: BoardRow[]) => {
    setRows(next)
    setOrderVersion((v) => v + 1)
  }, [])

  const applySolved = useCallback(
    (next: ScheduleInput, dayMap: Record<string, string[]>, pass1: Verdict[]) => {
      setSchedule(next)
      setRows(withTotals(buildRows(next, dayMap, pass1), next))
      setOrderVersion((v) => v + 1)
    },
    [],
  )

  // Lay the answer out when one arrives, once per job. Keying the effect on the job id makes
  // "once per solve" the mechanism rather than a guard against re-entry.
  const laidOut = useRef<string | null>(null)
  useEffect(() => {
    if (solver.phase !== 'done' || !solver.result || !solver.dayMap) return
    if (laidOut.current === solver.jobId) return
    laidOut.current = solver.jobId
    applySolved(schedule, solver.dayMap, solver.result.pass1)
  }, [solver.phase, solver.result, solver.dayMap, solver.jobId, applySolved, schedule])

  // An imported schedule arrives unarranged, so it solves itself once, on arrival. The import
  // page's button says "Confirm and solve" and this is the solve half of that sentence; before
  // this the board simply reloaded the demo and the reader's document went nowhere.
  const autoSolved = useRef(false)
  useEffect(() => {
    if (!imported || autoSolved.current) return
    autoSolved.current = true
    void solver.solve(imported)
    // solver identity changes on every render, so it is deliberately not a dependency: this runs
    // once per mount, guarded by the ref, and re-running it would restart a solve mid-flight.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [imported])

  // The solver is given the schedule, not our arrangement of it: the day assignment is what pass
  // 2 decides, so sending our arrangement would be asking it to confirm our own answer.
  const onSolve = useCallback(async () => {
    setUsedFallback(false)
    await solver.solve(schedule)
  }, [solver, schedule])

  const onFallback = useCallback(() => {
    applySolved(DEMO.schedule, DEMO.after.dayMap, DEMO.after.result.pass1)
    setUsedFallback(true)
  }, [applySolved])

  const onReset = useCallback(() => {
    // Reset goes back to the demo, and drops the imported schedule with it: a board that kept
    // silently reloading someone's document after they asked for a reset would be lying twice.
    clearImported()
    setImported(null)
    setSchedule(DEMO.schedule)
    setRows(withTotals(buildRows(DEMO.schedule, DEMO.before.dayMap, DEMO.before.verdicts), DEMO.schedule))
    setOrderVersion(0)
    laidOut.current = null
    setTransport(null)
    stream.clear()
    solver.reset()
    setUsedFallback(false)
  }, [solver, stream])

  const onPublish = useCallback(
    async (kind: SetEventKind, payload: Record<string, unknown>) => {
      const answer = await setEvent.publish(kind, payload, solver.jobId)
      if (!answer) return
      setTransport(answer.transport)
      // The event produced a new plan. Poll it the same way a solve is polled.
      await solver.adopt(answer.job_id)
    },
    [setEvent, solver],
  )

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
            data-testid="solve"
          >
            {solver.phase === 'solving' ? 'Solving' : 'Solve'}
          </ActionButton>
          <ActionButton onClick={onReset} variant="quiet" icon={<RotateCcw className="size-3.5" />} data-testid="reset">
            Reset
          </ActionButton>
        </div>
      </div>

      {solver.phase === 'failed' && (
        <div
          role="status"
          data-testid="solve-error"
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

      {imported && (
        <p className="script mt-6 border border-rail px-4 py-3 text-12 text-bone-dim" data-testid="imported-notice">
          This board is the schedule read from your document, not the demo. A scene record carries
          no day, so the days start empty and the solver places them. Reset returns to the demo.
        </p>
      )}

      {usedFallback && (
        <p className="script mt-6 border border-rail px-4 py-3 text-12 text-bone-dim" data-testid="fallback-notice">
          This is the run recorded on {DEMO.generatedAt.slice(0, 10)} at commit {DEMO.runSha}, not a
          live solve.
        </p>
      )}

      <dl className="mt-8 flex flex-wrap gap-x-12 gap-y-6">
        {imported ? (
          <>
            <Figure testId="figure-scenes" label="Scenes read" value={String(schedule.scenes.length)} />
            <Figure
              testId="figure-hold-days"
              label="Hold days"
              value={solvedPass2 ? String(solvedPass2.hold_days) : 'solving'}
            />
          </>
        ) : (
          <>
            <Figure
              testId="figure-hold-days"
              label="Hold days"
              from={String(DEMO.before.holdDays)}
              to={solvedPass2 ? String(solvedPass2.hold_days) : String(DEMO.before.holdDays)}
            />
            {/*
              Before a solve this figure states the problem in money rather than reporting its own
              absence. "Payroll removed: not solved" was the second thing a reader saw on the
              primary screen, and it read as something broken rather than as something not yet
              asked for. The hold cost of the plan currently on the board is a true and more
              useful number: it is what these four hold days cost at the published day rate, and
              it is the same figure that becomes "removed" once the solver has run.
            */}
            <Figure
              testId="figure-payroll"
              label={solvedPass2 ? 'Payroll removed' : 'Hold day cost'}
              value={dollars(
                solvedPass2 ? DEMO.before.holdingCents - solvedPass2.holding_cents : DEMO.before.holdingCents,
              )}
              source={solvedPass2 ? undefined : 'this plan, at the published day rate'}
            />
          </>
        )}
        <Figure
          testId="pass2-status"
          label="Pass 2"
          value={solvedPass2?.status ?? 'not run'}
          source={solvedPass2 ? `bound ${dollars(solvedPass2.bound)}` : undefined}
        />
        {solver.solveMs !== null && (
          <Figure testId="figure-solve-ms" label="Solve" value={`${Math.round(solver.solveMs)} ms`} />
        )}
      </dl>

      <div className="mt-8 overflow-hidden border border-rail">
        <Stripboard
          schedule={schedule}
          rows={rows}
          onRowsChange={onRowsChange}
          onOpenVerdict={setOpenDay}
          orderVersion={orderVersion}
        />
      </div>

      <div className="mt-5">
        <StripLegend />
      </div>

      <AskAgent schedule={schedule} />

      <SetEvents
        onPublish={onPublish}
        pending={setEvent.pending}
        error={setEvent.error}
        disabled={solver.jobId === null || solver.phase === 'solving'}
        lines={stream.lines}
        streamState={stream.state}
        jobId={solver.jobId}
        transport={transport}
      />

      <VerdictDialog
        verdict={openVerdict}
        date={openVerdict ? shootDate(schedule.days[openVerdict.day].date) : undefined}
        onClose={() => setOpenDay(null)}
      />

      <p className="script mt-10 text-11 text-bone-faint">
        Constructed demo data. Cast are letters, not names. The rule side is real. Removing the four
        hold days is worth {dollars(payrollRemovedCents)} at the published low-budget day rate.
      </p>
    </div>
  )
}
