/**
 * The mark: a camera gate. Four corner brackets frame a single strip.
 *
 * It is drawn as four separable quarters on purpose. The load-in animates each quarter in from
 * the gate panel that was covering it, so the mark assembles as the aperture opens.
 */
export type MarkQuarter = 'tl' | 'tr' | 'bl' | 'br'

const BRACKET: Record<MarkQuarter, string> = {
  tl: 'M2 12V4a2 2 0 0 1 2-2h8',
  tr: 'M28 2h8a2 2 0 0 1 2 2v8',
  bl: 'M2 28v8a2 2 0 0 0 2 2h8',
  br: 'M38 28v8a2 2 0 0 1-2 2h-8',
}

export function HoldMark({
  className,
  quarterClassName,
  title = 'HOLD',
}: {
  className?: string
  quarterClassName?: (q: MarkQuarter) => string | undefined
  title?: string
}) {
  return (
    <svg viewBox="0 0 40 40" className={className} role="img" aria-label={title}>
      <g fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="square">
        {(Object.keys(BRACKET) as MarkQuarter[]).map((q) => (
          <path key={q} d={BRACKET[q]} className={quarterClassName?.(q)} data-quarter={q} />
        ))}
      </g>
      <rect x="9" y="17.5" width="22" height="5" fill="currentColor" data-quarter="strip" />
    </svg>
  )
}
