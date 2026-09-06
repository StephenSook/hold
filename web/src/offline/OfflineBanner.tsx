import { CloudOff } from 'lucide-react'
import { useOnline } from './useOnline'

/**
 * What the viewer is looking at when the network is gone.
 *
 * The rule this exists to keep: the interface never claims fresh data. Offline it names the time
 * the cache was written, and when there is no cache it says that instead of showing an empty
 * screen and letting the viewer guess.
 */
export function OfflineBanner() {
  const { online, cachedAt } = useOnline()
  if (online) return null

  const time = cachedAt
    ? cachedAt.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', hour12: false })
    : null

  return (
    <div
      role="status"
      data-testid="offline-banner"
      className="script sticky top-[var(--header-h)] z-40 flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-flag bg-flag-deep px-5 py-2.5 text-11 text-bone sm:px-8"
    >
      <CloudOff className="size-3.5 shrink-0" aria-hidden="true" />
      <span className="font-bold tracking-[0.1em]">OFFLINE</span>
      <span>
        {time
          ? `Showing the plan cached as of ${time}. Nothing on screen is live.`
          : 'Nothing has been cached on this device yet, so there is nothing to show.'}
      </span>
    </div>
  )
}
