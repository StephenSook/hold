import { useEffect, useState } from 'react'
import { usePrefersReducedMotion } from './useReducedMotion'

/**
 * Count a figure from one value to another.
 *
 * The animation frame is the external system this synchronises with, so the effect starts and
 * stops the loop and nothing else. The resting value is derived rather than stored, which is why
 * there is no state to reset when the count is not running: under reduced motion, or before the
 * count starts, the figure is simply the value it should be.
 */
export function useCountTo(from: number, to: number, run: boolean, durationMs = 900): number {
  const reduced = usePrefersReducedMotion()
  const animate = run && !reduced && durationMs > 0
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    if (!animate) return
    let frame = 0
    const started = performance.now()
    const tick = (now: number) => {
      const t = Math.min(1, (now - started) / durationMs)
      setProgress(1 - Math.pow(1 - t, 3))
      if (t < 1) frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [animate, durationMs, from, to])

  if (!run) return from
  if (!animate) return to
  return from + (to - from) * progress
}
