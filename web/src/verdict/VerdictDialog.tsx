import { useEffect, useRef } from 'react'
import { X } from 'lucide-react'
import type { Verdict } from '@/types/contracts'
import { VerdictCard } from './VerdictCard'

/**
 * The verdict, in a native dialog.
 *
 * `showModal()` gives the focus trap, the Escape key, the inert background and the return of
 * focus to the opener for free, and gets them right in more cases than a hand-rolled trap does.
 */
export function VerdictDialog({
  verdict,
  date,
  onClose,
}: {
  verdict: Verdict | null
  date?: string
  onClose: () => void
}) {
  const ref = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (verdict && !dialog.open) dialog.showModal()
    if (!verdict && dialog.open) dialog.close()
  }, [verdict])

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      onClick={(event) => {
        // The backdrop is the dialog element itself, so a click that lands on it and not on the
        // card is a click outside.
        if (event.target === ref.current) onClose()
      }}
      aria-label={verdict ? `Verdict for day ${verdict.day + 1}` : 'Verdict'}
      className="m-auto max-h-[86dvh] w-[min(46rem,92vw)] border border-rail bg-board p-0 text-bone backdrop:bg-board/80 backdrop:backdrop-blur-sm"
    >
      {verdict && (
        <div className="relative flex max-h-[86dvh] flex-col">
          <button
            type="button"
            onClick={onClose}
            aria-label="Close the verdict"
            className="absolute top-2.5 right-2.5 z-10 flex size-8 cursor-pointer items-center justify-center text-bone transition-opacity hover:opacity-70"
          >
            <X className="size-4" aria-hidden="true" />
          </button>
          <VerdictCard verdict={verdict} date={date} />
        </div>
      )}
    </dialog>
  )
}
