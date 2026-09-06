import { useState } from 'react'
import { Check, CircleSlash, Diamond, ExternalLink, Plus } from 'lucide-react'
import type { Verdict, ViolationRecord } from '@/types/contracts'
import { hhmm } from '@/lib/format'
import { cn } from '@/lib/cn'

/**
 * The verdict for one shooting day.
 *
 * Two things share this card and they must never blend. The checker enumerates: every rule the
 * day breaks, with the limit, the computed value and the sentence from the source. The solver
 * explains: the rules that each alone make the day impossible. The card says which is which,
 * and it says plainly that the solver's core is sufficient rather than minimal, because that is
 * what OR-Tools documents and hiding it would make the stronger claim we cannot support.
 *
 * The quote is verbatim or it is not shown. It is set apart by a rule down its left edge so it
 * reads as somebody else's words, and the citation and the link sit under it.
 */
const STATUS = {
  LEGAL: { word: 'LEGAL', Icon: Check, slug: 'bg-board-3 text-bone' },
  ILLEGAL: { word: 'ILLEGAL', Icon: CircleSlash, slug: 'bg-flag-deep text-bone ring-1 ring-flag' },
  UNDETERMINED: { word: 'UNDETERMINED', Icon: Diamond, slug: 'bg-board-3 text-bone hatch' },
} as const

export function VerdictCard({ verdict, date }: { verdict: Verdict; date?: string }) {
  const { word, Icon, slug } = STATUS[verdict.status]
  const core = new Set(verdict.core_rule_ids)

  return (
    <article className="flex max-h-full flex-col bg-board text-bone">
      <header className={cn('flex flex-wrap items-center gap-x-4 gap-y-1 px-5 py-3', slug)}>
        <span className="script flex items-center gap-2 text-13 font-bold tracking-[0.14em]">
          <Icon className="size-4" aria-hidden="true" />
          {word}
        </span>
        <span className="script text-12 text-bone">
          DAY {verdict.day + 1}
          {date ? ` ${date}` : ''}
        </span>
        {verdict.status === 'ILLEGAL' && (
          <span className="script ml-auto text-12 text-bone">
            {verdict.violations.length} {verdict.violations.length === 1 ? 'RULE' : 'RULES'} BROKEN
          </span>
        )}
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {verdict.reason && (
          <p className="border-b border-rail px-5 py-4 text-14 text-bone-dim">{verdict.reason}</p>
        )}

        {verdict.status === 'LEGAL' && verdict.witness && <Witness verdict={verdict} />}

        {verdict.violations.length > 0 && (
          <ul className="divide-y divide-rail">
            {verdict.violations.map((violation) => (
              <Violation key={violation.rule_id} violation={violation} inCore={core.has(violation.rule_id)} />
            ))}
          </ul>
        )}

        {verdict.status === 'ILLEGAL' && verdict.core_rule_ids.length > 0 && (
          <p className="border-t border-rail px-5 py-4 text-13 text-bone-faint">
            The rules marked CORE come from the solver, which proves that each one alone makes this day
            impossible. That core is sufficient, not minimal: it can leave out a rule that is also broken.
            The list above comes from the independent checker, which enumerates every one.
          </p>
        )}
      </div>
    </article>
  )
}

function Violation({ violation, inCore }: { violation: ViolationRecord; inCore: boolean }) {
  const [open, setOpen] = useState(false)
  return (
    <li>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        data-testid={`violation-${violation.rule_id}`}
        className="group flex w-full cursor-pointer items-start gap-3 px-5 py-4 text-left transition-colors hover:bg-board-2"
      >
        <span className="mt-0.5 shrink-0 text-bone-faint transition-colors group-hover:text-bone">
          {open ? <Plus className="size-4 rotate-45" aria-hidden="true" /> : <Plus className="size-4" aria-hidden="true" />}
        </span>
        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <span className="text-15 font-semibold text-bone">{violation.title}</span>
            {inCore && (
              <span className="script border border-flag px-1.5 py-px text-10 tracking-[0.12em] text-flag">CORE</span>
            )}
          </span>
          <span className="script mt-1.5 flex flex-wrap gap-x-5 gap-y-1 text-12 text-bone-dim">
            <span>
              <span className="text-bone-faint">LIMIT </span>
              {violation.limit}
            </span>
            <span>
              <span className="text-bone-faint">COMPUTED </span>
              {violation.computed}
            </span>
            {/* The figure is bone and the red is a bar beside it. Red type at this size clears
                the graphic floor and not the AAA bar this card is held to, and the colour was
                never the signal anyway. */}
            <span className="flex items-center gap-1.5">
              <span aria-hidden="true" className="inline-block h-3 w-0.5 bg-flag" />
              <span className="text-bone-faint">OVER BY </span>
              <span className="font-bold text-bone">{violation.over_by}</span>
            </span>
          </span>
          <span className="script mt-1.5 block text-11 text-bone-faint">
            {violation.jurisdiction} {violation.citation}
          </span>
        </span>
      </button>

      {open && (
        <div className="px-5 pb-5 pl-12">
          <blockquote className="border-l-2 border-bone-faint pl-4 text-14 leading-relaxed text-bone">
            {violation.quote}
          </blockquote>
          <a
            href={violation.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="script mt-3 inline-flex items-center gap-1.5 text-11 text-bone-dim underline decoration-rail underline-offset-4 transition-colors hover:text-bone hover:decoration-bone"
          >
            {violation.citation}
            <ExternalLink className="size-3" aria-hidden="true" />
          </a>
        </div>
      )}
    </li>
  )
}

/**
 * The witness: the legal call sheet the solver found. It is the answer to "prove it", and for a
 * day with a minor it carries the times that decide the day, including the dismissal, which an
 * assistant director calls the pumpkin.
 */
function Witness({ verdict }: { verdict: Verdict }) {
  const witness = verdict.witness
  if (!witness) return null
  const minors = Object.entries(witness.minors ?? {})
  return (
    <div className="border-b border-rail px-5 py-4">
      <p className="script text-11 tracking-[0.12em] text-bone-faint">A LEGAL TIMING, CHECKED</p>
      <dl className="script mt-3 grid grid-cols-2 gap-x-6 gap-y-2 text-12 sm:grid-cols-4">
        <Field label="CREW CALL" value={hhmm(witness.crew_call)} />
        <Field label="WRAP" value={hhmm(witness.crew_wrap)} />
        <Field label="SCENES" value={String(witness.scenes.length)} />
        <Field label="MINORS" value={String(minors.length)} />
      </dl>

      {minors.length > 0 && (
        <ul className="script mt-4 space-y-2 text-12">
          {minors.map(([castId, minor]) => (
            <li key={castId} className="flex flex-wrap gap-x-5 gap-y-1 border-t border-rail-soft pt-2">
              <span className="font-bold">CAST {castId.replace(/^c/, '')}K</span>
              <span>
                <span className="text-bone-faint">CALL </span>
                {hhmm(minor.call)}
              </span>
              <span>
                <span className="text-bone-faint">PUMPKIN </span>
                {hhmm(minor.dismiss)}
              </span>
              <span>
                <span className="text-bone-faint">WORK </span>
                {Math.floor(minor.work_minutes / 60)}h {minor.work_minutes % 60}m
              </span>
              <span>
                <span className="text-bone-faint">AT LOCATION </span>
                {Math.floor(minor.location_minutes / 60)}h {minor.location_minutes % 60}m
              </span>
            </li>
          ))}
        </ul>
      )}

      {witness.heuristic && <p className="mt-3 text-11 text-bone-faint">{witness.heuristic}</p>}
    </div>
  )
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-10 tracking-[0.12em] text-bone-faint">{label}</dt>
      <dd className="mt-0.5 tabular-nums">{value}</dd>
    </div>
  )
}
