import { del, get, set } from 'idb-keyval'
import type { PersistedClient, Persister } from '@tanstack/react-query-persist-client'

/**
 * The query cache, in IndexedDB.
 *
 * localStorage would be simpler and is the wrong store: it is synchronous, so writing a solved
 * schedule to it blocks the main thread on the frame after a solve, and it is capped at a few
 * megabytes. `idb-keyval` is a thin async wrapper over IndexedDB and is already a dependency.
 *
 * Every operation swallows its own failure on purpose. A browser in private mode, or one with
 * site data blocked, throws on the accessor itself, and an offline cache that cannot be written
 * is a degraded experience, never a broken page.
 */
const KEY = 'hold.query-cache.v1'

export function indexedDbPersister(): Persister {
  return {
    persistClient: async (client: PersistedClient) => {
      try {
        await set(KEY, client)
      } catch {
        /* storage refused: the app keeps working, it just will not be readable offline */
      }
    },
    restoreClient: async () => {
      try {
        return await get<PersistedClient>(KEY)
      } catch {
        return undefined
      }
    },
    removeClient: async () => {
      try {
        await del(KEY)
      } catch {
        /* nothing to remove, or storage refused */
      }
    },
  }
}

/** When the cache was last written, or null when nothing has been cached. */
export async function cachedAt(): Promise<Date | null> {
  try {
    const stored = await get<PersistedClient>(KEY)
    return stored?.timestamp ? new Date(stored.timestamp) : null
  } catch {
    return null
  }
}
