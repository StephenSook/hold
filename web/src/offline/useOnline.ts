import { useEffect, useState } from 'react'
import { cachedAt } from './persister'

export interface OfflineState {
  online: boolean
  /** When the cache this page can fall back on was written, or null when there is none. */
  cachedAt: Date | null
}

/**
 * Whether the browser thinks it is online, and how old the fallback is.
 *
 * `navigator.onLine` is a weak signal: it reports the network interface, not reachability, so it
 * can say true behind a captive portal. It is used only to decide what to TELL the viewer, never
 * to decide whether to try: the request is always attempted and its real failure is what shows.
 */
export function useOnline(): OfflineState {
  const [online, setOnline] = useState(() => (typeof navigator === 'undefined' ? true : navigator.onLine))
  const [at, setAt] = useState<Date | null>(null)

  useEffect(() => {
    const up = () => setOnline(true)
    const down = () => setOnline(false)
    window.addEventListener('online', up)
    window.addEventListener('offline', down)
    return () => {
      window.removeEventListener('online', up)
      window.removeEventListener('offline', down)
    }
  }, [])

  useEffect(() => {
    let alive = true
    const read = () => {
      void cachedAt().then((value) => {
        if (alive) setAt(value)
      })
    }
    read()
    const timer = setInterval(read, 15_000)
    return () => {
      alive = false
      clearInterval(timer)
    }
  }, [])

  return { online, cachedAt: at }
}
