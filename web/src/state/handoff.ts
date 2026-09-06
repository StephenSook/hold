import type { ScheduleInput } from '@/types/contracts'

/**
 * The schedule the import page confirmed, handed to the board.
 *
 * Before this existed, "Confirm and solve" set a boolean and printed a sentence. The extracted
 * schedule lived in the import page's own state and was dropped when the page unmounted, while
 * the board seeded unconditionally from the committed demo fixture. So the agent read your
 * document, showed you four counts, and threw the answer away, and the claim that the document
 * becomes the input was false in the shipped product.
 *
 * sessionStorage rather than a router location: the board is a deep link, and a reader who
 * refreshes it should still be looking at their own schedule rather than silently reverting to
 * the demo. It clears on reset and when the tab closes, which is the right lifetime for a
 * schedule nobody has been asked to store.
 */
const KEY = 'hold.imported-schedule'

/** Every accessor is wrapped: a private window, or a browser set to block site data, throws on read. */
export function putImported(schedule: ScheduleInput): void {
  try {
    sessionStorage.setItem(KEY, JSON.stringify(schedule))
  } catch {
    // The handoff is a convenience. Losing it costs a re-import, not correctness.
  }
}

export function getImported(): ScheduleInput | null {
  try {
    const raw = sessionStorage.getItem(KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as ScheduleInput
    // A stored value from an older shape would render an empty board with no explanation.
    if (!Array.isArray(parsed?.scenes) || !Array.isArray(parsed?.days)) return null
    return parsed
  } catch {
    return null
  }
}

export function clearImported(): void {
  try {
    sessionStorage.removeItem(KEY)
  } catch {
    // Nothing to do. The next read either finds it or does not.
  }
}
