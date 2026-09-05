import { useEffect, useMemo, useState } from 'react'
import { ArrowRight, FileText, Play } from 'lucide-react'
import { Reveal } from '@/components/Reveal'
import { ActionAnchor, ActionLink } from '@/components/Action'
import { Figure } from '@/components/Figure'
import { Stripboard } from '@/board/Stripboard'
import { buildRows, withTotals, type BoardRow } from '@/board/model'
import { VerdictCard } from '@/verdict/VerdictCard'
import { DEMO, payrollRemovedCents } from '@/state/demo'
import { useInView } from '@/hooks/useInView'
import { useCountTo } from '@/hooks/useCountTo'
import { useStatus } from '@/hooks/useStatus'
import { dollars, shootDate } from '@/lib/format'
import { StripLegend } from '@/board/StripLegend'

const REPO = 'https://github.com/StephenSook/hold'

/** Days that actually carry a scene. An empty day costs nothing and is not shot. */
function usedDays(dayMap: Record<string, string[]>): number {
  return Object.values(dayMap).filter((ids) => ids.length > 0).length
}

export function Landing() {
  return (
    <>
      <Hero />
      <TheBoard />
      <TheVerdict />
      <TheResidual />
      <Honesty />
    </>
  )
}

/**
 * The hero states what the tool does for the person using it, in the words they would use, and
 * nothing else. The framing marks are the film camera's frame lines, which is also the mark.
 */
function Hero() {
  return (
    <section className="relative mx-auto max-w-[1440px] px-5 pt-16 pb-20 sm:px-8 sm:pt-24 sm:pb-28">
      <FrameMarks />
      <p className="script-label text-11 text-bone-faint">
        A shooting schedule that pays for itself
      </p>
      <Reveal
        as="h1"
        delay={0.1}
        className="display-wide mt-6 max-w-[19ch] text-48 text-bone sm:text-64 lg:text-88"
        lines={['The cheapest order', 'you can legally shoot.']}
      />
      <p className="mt-7 max-w-[62ch] text-16 text-bone-dim sm:text-18">
        HOLD reorders the board to the provably lowest hold-day cost, then checks every day against
        child-performer law and the union agreement. When a day is not legal it names each rule it
        breaks and puts the sentence from the statute on screen.
      </p>
      <div className="mt-9 flex flex-wrap items-center gap-3">
        <ActionLink to="/board" icon={<Play className="size-3.5" />}>
          Open the board
        </ActionLink>
        <ActionLink to="/judge" variant="quiet" icon={<FileText className="size-3.5" />}>
          Judge walkthrough
        </ActionLink>
      </div>
    </section>
  )
}

/** The frame lines a camera operator sees through the gate. They are the mark, at page scale. */
function FrameMarks() {
  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-x-5 inset-y-0 sm:inset-x-8">
      <span className="absolute top-0 left-0 h-4 w-px bg-rail" />
      <span className="absolute top-0 left-0 h-px w-4 bg-rail" />
      <span className="absolute top-0 right-0 h-4 w-px bg-rail" />
      <span className="absolute top-0 right-0 h-px w-4 bg-rail" />
      <span className="absolute bottom-0 left-0 h-4 w-px bg-rail" />
      <span className="absolute bottom-0 left-0 h-px w-4 bg-rail" />
      <span className="absolute right-0 bottom-0 h-4 w-px bg-rail" />
      <span className="absolute right-0 bottom-0 h-px w-4 bg-rail" />
    </div>
  )
}

/**
 * The one orchestrated moment.
 *
 * The board holds the hand-built order: four performers paid to wait, one day that cannot legally
 * be shot. When the section is reached the solved order arrives and every strip travels at once
 * while the two figures count down. Nothing else on this page moves unless somebody asks it to.
 */
function TheBoard() {
  const [ref, seen] = useInView<HTMLDivElement>()
  const [solved, setSolved] = useState(false)

  const beforeRows = useMemo(
    () => withTotals(buildRows(DEMO.schedule, DEMO.before.dayMap, DEMO.before.verdicts), DEMO.schedule),
    [],
  )
  const afterRows = useMemo(
    () => withTotals(buildRows(DEMO.schedule, DEMO.after.dayMap, DEMO.after.result.pass1), DEMO.schedule),
    [],
  )
  const [rows, setRows] = useState<BoardRow[]>(beforeRows)

  useEffect(() => {
    if (!seen || solved) return
    const timer = setTimeout(() => {
      setRows(afterRows)
      setSolved(true)
    }, 1100)
    return () => clearTimeout(timer)
  }, [seen, solved, afterRows])

  const holdDays = useCountTo(DEMO.before.holdDays, solved ? 0 : DEMO.before.holdDays, seen, 700)
  const money = useCountTo(0, solved ? payrollRemovedCents : 0, seen, 900)

  return (
    <section ref={ref} className="border-y border-rail">
      <div className="mx-auto max-w-[1440px] px-5 py-14 sm:px-8 sm:py-20">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <p className="script-label text-11 text-bone-faint">The board</p>
            <h2 className="display-wide mt-3 max-w-[24ch] text-28 text-bone sm:text-36">
              Four performers were paid to wait. Now none are.
            </h2>
          </div>
          <dl className="flex flex-wrap gap-x-10 gap-y-5">
            <Figure
              label="Hold days"
              from={String(DEMO.before.holdDays)}
              to={String(Math.round(holdDays))}
              source="recounted from the day map"
            />
            <Figure
              label="Payroll removed"
              value={dollars(Math.round(money))}
              source="SAG-AFTRA low budget day rate"
            />
            <Figure
              label="Illegal days"
              from="1"
              to={solved ? '0' : '1'}
              source="checked, every rule named"
            />
            <Figure
              label="Shoot days used"
              from={String(usedDays(DEMO.before.dayMap))}
              to={String(usedDays(solved ? DEMO.after.dayMap : DEMO.before.dayMap))}
              source="a shorter shoot is the same saving twice"
            />
          </dl>
        </div>

        <div className="mt-8 overflow-hidden border border-rail">
          <Stripboard
            schedule={DEMO.schedule}
            rows={rows}
            onRowsChange={setRows}
            onOpenVerdict={() => {}}
            orderVersion={solved ? 1 : 0}
            label="The demo shooting schedule, before and after the solve"
          />
        </div>

        <div className="mt-5 flex flex-wrap items-center justify-between gap-4">
          <StripLegend />
          <p className="script text-11 text-bone-faint">
            {solved
              ? `Solved: ${DEMO.after.result.pass2.status.toLowerCase()}, the checker agrees`
              : 'The hand-built order, as an assistant director would write it by set and time of day'}
          </p>
        </div>
      </div>
    </section>
  )
}

/** The other half of the product: the day that cannot be shot, and every rule it breaks. */
function TheVerdict() {
  const illegal = DEMO.before.verdicts.find((v) => v.status === 'ILLEGAL')
  if (!illegal) return null
  return (
    <section className="mx-auto max-w-[1440px] px-5 py-14 sm:px-8 sm:py-20">
      <div className="grid gap-10 lg:grid-cols-[minmax(0,26rem)_minmax(0,1fr)]">
        <div>
          <p className="script-label text-11 text-bone-faint">The verdict</p>
          <h2 className="display-wide mt-3 text-28 text-bone sm:text-36">
            A day that cannot be shot, and why.
          </h2>
          <p className="mt-5 max-w-[52ch] text-16 text-bone-dim">
            Every rule carries its citation, the limit it sets, the value we computed, and the
            sentence from the source. Open one and you read the statute, not our summary of it.
          </p>
          <p className="script mt-5 text-11 text-bone-faint">
            Day {illegal.day + 1}, {shootDate(DEMO.schedule.days[illegal.day].date)}.{' '}
            {illegal.violations.length} rules broken across{' '}
            {new Set(illegal.violations.map((v) => v.jurisdiction)).size} jurisdictions.
          </p>
          <div className="mt-7">
            <ActionLink to={`/day/${illegal.day}`} variant="quiet" icon={<ArrowRight className="size-3.5" />}>
              Open the day
            </ActionLink>
          </div>
        </div>
        <div className="border border-rail">
          <VerdictCard verdict={illegal} date={shootDate(DEMO.schedule.days[illegal.day].date)} />
        </div>
      </div>
    </section>
  )
}

/** The claim a stranger can check without an account: eight published optima, reproduced. */
function TheResidual() {
  const { data, isError } = useStatus()
  const matched = data?.benchmark_matched ?? DEMO.after.result.benchmark?.instance ?? '8/8'
  return (
    <section className="border-y border-rail">
      <div className="mx-auto max-w-[1440px] px-5 py-14 sm:px-8 sm:py-20">
        <p className="script-label text-11 text-bone-faint">The residual</p>
        <h2 className="display-wide mt-3 max-w-[26ch] text-28 text-bone sm:text-36">
          Eight published optima. Difference of zero.
        </h2>
        <p className="mt-5 max-w-[62ch] text-16 text-bone-dim">
          The solver runs against the proven optima of the academic talent-scheduling benchmark on
          every push, in continuous integration, with no key and no account. You can clone the
          repository and run the same suite.
        </p>
        <dl className="mt-8 flex flex-wrap gap-x-12 gap-y-6">
          <Figure label="Benchmark matched" value={matched} source="bench/results.json" />
          <Figure
            label="Solve"
            value={data ? `${Math.round(data.headline.solve_ms)} ms` : 'live'}
            source={isError ? 'API unreachable, showing the recorded run' : '/api/status'}
          />
          <Figure
            label="Optimality"
            value={DEMO.after.result.pass2.status}
            source="proven on the benchmark model only"
          />
        </dl>
        <div className="mt-8 flex flex-wrap gap-3">
          <ActionAnchor href={`${REPO}/actions/workflows/ci.yml`}>Continuous integration</ActionAnchor>
          <ActionAnchor href="./api/status">Live status</ActionAnchor>
        </div>
      </div>
    </section>
  )
}

/** What this does not claim. It ships on the page rather than in a footnote. */
function Honesty() {
  const items = [
    'Optimality is proven on the benchmark model. The extended model reports the best found with the solver bound. The two are never blended.',
    'The demo schedule is constructed and says so. Cast are letters, not names. No public corpus of real stripboards was found.',
    'The solver core explains why no legal timing exists and is sufficient, not minimal. The independent checker lists every violation.',
    'Louisiana hour caps are unverified, so the registry refuses them rather than guessing.',
    'The solver runs on the server. The phone displays and caches, and labels a cached answer with its time.',
    'No industry-wide savings figure is published. We do not have one.',
  ]
  return (
    <section className="mx-auto max-w-[1440px] px-5 py-14 sm:px-8 sm:py-20">
      <p className="script-label text-11 text-bone-faint">What this does not claim</p>
      <ul className="mt-6 grid gap-x-12 gap-y-5 sm:grid-cols-2">
        {items.map((item) => (
          <li key={item} className="flex gap-3 text-14 text-bone-dim">
            <span aria-hidden="true" className="mt-2.5 h-px w-4 shrink-0 bg-rail" />
            <span className="max-w-[54ch]">{item}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}
