import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import type { MarkQuarter } from './HoldMark'
import { usePrefersReducedMotion } from '@/hooks/useReducedMotion'

/**
 * The load-in: a camera gate.
 *
 * Four panels hold the frame closed while the fonts load, the mark assembles from the four
 * quarters those panels were covering, and the counter runs to the figure the site exists to
 * prove. Then the gate opens as an aperture and does not return this session.
 *
 * It is capped at about 1.6 seconds, and skipped outright on a repeat view or when the viewer
 * has asked for reduced motion, because a load-in that delays first paint is a cost the viewer
 * pays and the designer does not.
 */
const SEEN_KEY = 'hold.gate.seen'
const HOLD_MS = 1150
const OPEN_S = 0.72
const GATE_EASE = [0.76, 0, 0.24, 1] as const
const QUARTER_EASE = [0.22, 1, 0.36, 1] as const

const BRACKETS: Record<MarkQuarter, string> = {
  tl: 'M2 12V4a2 2 0 0 1 2-2h8',
  tr: 'M28 2h8a2 2 0 0 1 2 2v8',
  bl: 'M2 28v8a2 2 0 0 0 2 2h8',
  br: 'M38 28v8a2 2 0 0 1-2 2h-8',
}

const QUARTER_FROM: Record<MarkQuarter, { x: number; y: number }> = {
  tl: { x: -14, y: -14 },
  tr: { x: 14, y: -14 },
  bl: { x: -14, y: 14 },
  br: { x: 14, y: 14 },
}

const QUARTERS = Object.keys(BRACKETS) as MarkQuarter[]

function seenThisSession(): boolean {
  try {
    return sessionStorage.getItem(SEEN_KEY) === '1'
  } catch {
    return false
  }
}

function markSeen(): void {
  try {
    sessionStorage.setItem(SEEN_KEY, '1')
  } catch {
    /* private mode: the gate simply plays again */
  }
}

export function Gate({ onOpened }: { onOpened?: () => void }) {
  const reduced = usePrefersReducedMotion()
  const [closed, setClosed] = useState(() => !seenThisSession() && !reduced)
  const [matched, setMatched] = useState(0)

  // The counter runs to 8: the benchmark instances whose published optimum the solver
  // reproduces. It is the site's first claim, made before the site has finished loading.
  useEffect(() => {
    if (!closed) return
    let step = 0
    const tick = setInterval(() => {
      step += 1
      setMatched(step)
      if (step >= 8) clearInterval(tick)
    }, 78)
    return () => clearInterval(tick)
  }, [closed])

  useEffect(() => {
    if (!closed) {
      onOpened?.()
      return
    }
    let cancelled = false
    const fontsReady =
      typeof document !== 'undefined' && 'fonts' in document ? document.fonts.ready : Promise.resolve()
    const minimum = new Promise<void>((resolve) => setTimeout(resolve, HOLD_MS))
    void Promise.all([fontsReady, minimum]).then(() => {
      if (!cancelled) {
        markSeen()
        setClosed(false)
      }
    })
    return () => {
      cancelled = true
    }
  }, [closed, onOpened])

  return (
    <AnimatePresence onExitComplete={onOpened}>
      {closed && (
        <motion.div key="gate" className="fixed inset-0 z-[200]" aria-hidden="true" initial={false}>
          {/* Four panels. Each carries a hairline on its inner edge, so what the eye reads on
              opening is four rules retreating, which is what a gate does. */}
          <motion.div
            className="absolute inset-y-0 left-0 w-1/2 border-r border-rail bg-board"
            exit={{ x: '-100%', transition: { duration: OPEN_S, ease: GATE_EASE } }}
          />
          <motion.div
            className="absolute inset-y-0 right-0 w-1/2 border-l border-rail bg-board"
            exit={{ x: '100%', transition: { duration: OPEN_S, ease: GATE_EASE } }}
          />
          <motion.div
            className="absolute inset-x-0 top-0 h-1/2 border-b border-rail bg-board"
            exit={{ y: '-100%', transition: { duration: OPEN_S, ease: GATE_EASE, delay: 0.06 } }}
          />
          <motion.div
            className="absolute inset-x-0 bottom-0 h-1/2 border-t border-rail bg-board"
            exit={{ y: '100%', transition: { duration: OPEN_S, ease: GATE_EASE, delay: 0.06 } }}
          />

          <motion.div
            className="absolute inset-0 flex flex-col items-center justify-center gap-5"
            exit={{ opacity: 0, transition: { duration: 0.22 } }}
          >
            <svg viewBox="0 0 40 40" className="h-14 w-14 text-bone">
              <g fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="square">
                {QUARTERS.map((q, i) => (
                  <motion.path
                    key={q}
                    d={BRACKETS[q]}
                    initial={{ opacity: 0, x: QUARTER_FROM[q].x, y: QUARTER_FROM[q].y }}
                    animate={{
                      opacity: 1,
                      x: 0,
                      y: 0,
                      transition: { duration: 0.5, delay: 0.05 * i, ease: QUARTER_EASE },
                    }}
                  />
                ))}
              </g>
              <motion.rect
                x="9"
                y="17.5"
                width="22"
                height="5"
                fill="currentColor"
                initial={{ scaleX: 0 }}
                animate={{ scaleX: 1, transition: { duration: 0.55, delay: 0.28, ease: QUARTER_EASE } }}
                style={{ transformOrigin: '9px 20px' }}
              />
            </svg>
            <motion.span
              className="script-label text-11 text-bone-dim"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1, transition: { delay: 0.2, duration: 0.3 } }}
            >
              BENCHMARK RESIDUAL {matched}/8
            </motion.span>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
