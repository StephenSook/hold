import { forwardRef } from 'react'
import type { HTMLAttributes } from 'react'
import { Check, CircleSlash, Diamond } from 'lucide-react'
import type { ScheduleInput, Verdict } from '@/types/contracts'
import { eighths, hhmm, shootDate } from '@/lib/format'
import { cn } from '@/lib/cn'

/**
 * The day break.
 *
 * On a physical board this is the slat that marks where one shooting day ends, and everything
 * between two of them is one day. In every product on the market it is the only full-bleed dark
 * row on the board, which makes it the board's heartbeat, so it carries the day's totals and the
 * day's verdict and nothing else competes with it.
 *
 * The verdict is the reason this product exists, so it is stated here in words. LEGAL is quiet,
 * because legality is the default state and only failure is news. ILLEGAL is a filled slug in
 * oxblood with bone type, which is the only pairing in this palette that clears 7:1 while still
 * reading as a stamp. UNDETERMINED is hatched rather than coloured, because it is the absence of
 * a proof rather than a warning.
 *
 * The bright red is a graphic and never a text colour: it clears the 3:1 floor for a rule or a
 * bar on this ground and does not clear 7:1 for type, so the slug is oxblood, the ring is bright,
 * and the word sits in bone on oxblood or oxblood on bone.
 */
export interface DayBreakProps extends HTMLAttributes<HTMLDivElement> {
  day: number
  dayCount: number
  schedule: ScheduleInput
  sceneIds: string[]
  pagesEighths: number
  verdict: Verdict | null
  onOpenVerdict?: (day: number) => void
}

export const DayBreak = forwardRef<HTMLDivElement, DayBreakProps>(function DayBreak(
  { day, dayCount, schedule, sceneIds, pagesEighths, verdict, onOpenVerdict, className, ...rest },
  ref,
) {
  const shootDay = schedule.days[day]
  const used = sceneIds.length > 0
  const status = used ? (verdict?.status ?? null) : null
  const illegal = status === 'ILLEGAL'
  const undetermined = status === 'UNDETERMINED'

  return (
    <div
      ref={ref}
      {...rest}
      data-testid={`day-break-${day}`}
      data-day={day}
      data-status={status ?? 'EMPTY'}
      className={cn(
        'script relative flex flex-wrap items-center gap-x-4 gap-y-1 px-2.5 py-2 text-11 sm:h-10 sm:flex-nowrap sm:py-0',
        illegal
          ? 'bg-flag-deep text-bone shadow-[inset_0_0_0_1px_var(--color-flag)]'
          : 'bg-board-3 text-bone',
        undetermined && 'hatch',
        !used && 'text-bone-faint',
        className,
      )}
    >
      <span className="font-bold tracking-[0.1em] whitespace-nowrap">
        {used ? `END OF DAY ${day + 1}` : `DAY ${day + 1}`}
        <span className="font-normal"> OF {dayCount}</span>
      </span>

      <span className="whitespace-nowrap">{shootDate(shootDay.date)}</span>

      <span className="tabular-nums whitespace-nowrap">{eighths(pagesEighths)} PGS</span>

      <span className="hidden tabular-nums whitespace-nowrap sm:inline">
        CALL {hhmm(shootDay.call)} WRAP {hhmm(shootDay.wrap)}
      </span>

      {shootDay.school_day && (
        <span className="hidden whitespace-nowrap sm:inline">SCHOOL DAY</span>
      )}

      <span className="ml-auto flex items-center gap-2 whitespace-nowrap">
        {!used && <span>NO SCENES</span>}

        {status === 'LEGAL' && (
          <span className="flex items-center gap-1.5">
            <Check className="size-3.5" aria-hidden="true" />
            LEGAL
          </span>
        )}

        {undetermined && (
          <span className="flex items-center gap-1.5">
            <Diamond className="size-3.5" aria-hidden="true" />
            UNDETERMINED
          </span>
        )}

        {illegal && (
          <button
            type="button"
            onClick={() => onOpenVerdict?.(day)}
            data-testid={`open-verdict-${day}`}
            className="flex cursor-pointer items-center gap-1.5 bg-bone px-2 py-0.5 font-bold text-flag-deep transition-opacity hover:opacity-85"
          >
            <CircleSlash className="size-3.5" aria-hidden="true" />
            ILLEGAL
            <span>
              {verdict?.violations.length} {verdict?.violations.length === 1 ? 'RULE' : 'RULES'}
            </span>
          </button>
        )}
      </span>
    </div>
  )
})
