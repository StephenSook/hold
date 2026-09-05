import { useEffect } from 'react'
import Lenis from 'lenis'
import { usePrefersReducedMotion } from './useReducedMotion'

/**
 * Smoothed scrolling, on the reading routes only.
 *
 * Hijacked scroll is wrong on a working surface: an assistant director dragging a strip needs
 * the page to answer the wheel exactly, and a day view read on set needs native momentum. So
 * the marketing route asks for it and the board, the day view and the judge page do not, and
 * nobody gets it when they have asked for reduced motion.
 */
export function useSmoothScroll(enabled: boolean): void {
  const reduced = usePrefersReducedMotion()

  useEffect(() => {
    if (!enabled || reduced) return
    const lenis = new Lenis({
      duration: 1.05,
      easing: (t: number) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      smoothWheel: true,
      touchMultiplier: 1.6,
    })
    let frame = 0
    const raf = (time: number) => {
      lenis.raf(time)
      frame = requestAnimationFrame(raf)
    }
    frame = requestAnimationFrame(raf)
    document.documentElement.classList.add('lenis-on')
    return () => {
      cancelAnimationFrame(frame)
      lenis.destroy()
      document.documentElement.classList.remove('lenis-on')
    }
  }, [enabled, reduced])
}
