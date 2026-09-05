import { cn } from '@/lib/cn'

/**
 * A number with its label and, where there is one, the file it was read from. The source line
 * is not decoration: no headline number in this project is typed by hand, and printing where
 * each one came from is how a stranger checks that.
 */
export function Figure({
  label,
  value,
  from,
  to,
  source,
  className,
}: {
  label: string
  value?: string
  from?: string
  to?: string
  source?: string
  className?: string
}) {
  return (
    <div className={cn('flex flex-col gap-1.5', className)}>
      <dt className="script-label text-10 text-bone-faint">{label}</dt>
      <dd className="script flex items-baseline gap-2 text-bone">
        {from !== undefined && from !== to ? (
          <>
            <span className="text-22 text-bone-faint line-through decoration-flag decoration-2">{from}</span>
            <span className="text-11 text-bone-faint">to</span>
            <span className="text-28 font-bold">{to}</span>
          </>
        ) : (
          <span className="text-28 font-bold">{from !== undefined ? to : value}</span>
        )}
      </dd>
      {source && <dd className="script text-10 text-bone-faint">{source}</dd>}
    </div>
  )
}
