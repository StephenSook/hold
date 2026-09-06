import { useRegisterSW } from 'virtual:pwa-register/react'
import { RefreshCw } from 'lucide-react'

/**
 * The service worker's update path, and its way out.
 *
 * A precached shell is sticky: a returning viewer keeps the version their browser already has,
 * so a bad deploy survives a redeploy in their browser and there is no way to tell them. This is
 * that way. `registerType: 'prompt'` means a new build never swaps itself in silently, and the
 * button both takes the update and reloads, which is the kill switch for a bad shell.
 */
export function UpdatePrompt() {
  const {
    needRefresh: [needRefresh, setNeedRefresh],
    updateServiceWorker,
  } = useRegisterSW({
    onRegisteredSW(_url, registration) {
      // Ask the browser hourly. Without this a tab open all day never learns a new build exists.
      if (registration) setInterval(() => void registration.update(), 60 * 60_000)
    },
  })

  if (!needRefresh) return null

  return (
    <div
      role="status"
      data-testid="update-prompt"
      className="script sticky top-[var(--header-h)] z-40 flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-rail bg-board-3 px-5 py-2.5 text-11 text-bone sm:px-8"
    >
      <RefreshCw className="size-3.5 shrink-0" aria-hidden="true" />
      <span>A newer version of HOLD is available.</span>
      <button
        type="button"
        onClick={() => void updateServiceWorker(true)}
        className="script-label cursor-pointer border border-edge px-3 py-1 text-10 text-bone transition-colors hover:border-bone"
      >
        Reload
      </button>
      <button
        type="button"
        onClick={() => setNeedRefresh(false)}
        className="script-label cursor-pointer text-10 text-bone-dim underline decoration-rail underline-offset-4 transition-colors hover:text-bone"
      >
        Not now
      </button>
    </div>
  )
}
