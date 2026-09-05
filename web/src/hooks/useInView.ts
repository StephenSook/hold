import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * Fires once, when the element first crosses into view.
 *
 * The observer is attached from a callback ref rather than an effect, so the element is known the
 * moment React commits it, and where IntersectionObserver does not exist the initial state is
 * simply true rather than something an effect has to correct after the first paint.
 */
export function useInView<T extends Element>(margin = '-25% 0px -25% 0px') {
  const supported = typeof IntersectionObserver !== 'undefined'
  const [seen, setSeen] = useState(!supported)
  const observer = useRef<IntersectionObserver | null>(null)

  const ref = useCallback(
    (node: T | null) => {
      observer.current?.disconnect()
      observer.current = null
      if (!node || !supported) return
      const next = new IntersectionObserver(
        (entries) => {
          if (entries.some((entry) => entry.isIntersecting)) {
            setSeen(true)
            next.disconnect()
          }
        },
        { rootMargin: margin },
      )
      next.observe(node)
      observer.current = next
    },
    [margin, supported],
  )

  useEffect(() => () => observer.current?.disconnect(), [])

  return [ref, seen] as const
}
