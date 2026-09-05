import { cn } from '@/lib/cn'

/**
 * A label that swaps for its own copy on hover: the visible line rises out of a clip and its
 * duplicate rises in behind it. The duplicate is aria-hidden, so a screen reader hears the
 * string once.
 *
 * No colour changes. The interface has no brand hue, so an affordance is signalled by motion
 * and by inversion, never by turning something a brand colour on hover.
 */
export function SwapText({ children, className }: { children: string; className?: string }) {
  return (
    <span className={cn('relative inline-block overflow-hidden align-bottom', className)}>
      <span className="relative block transition-transform duration-400 ease-in-out group-hover/swap:-translate-y-full group-focus-visible/swap:-translate-y-full">
        <span className="block">{children}</span>
        <span className="absolute inset-0 top-full block" aria-hidden="true">
          {children}
        </span>
      </span>
    </span>
  )
}
