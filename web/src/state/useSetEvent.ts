import { useCallback, useState } from 'react'
import { ApiError, apiFetch } from '@/lib/api'
import type { SetEventKind, SetEventSource } from '@/types/contracts'

export interface SetEventResponse {
  job_id: string
  base_job_id: string
  change: string
  poll: string
  transport: string
}

/**
 * Publish an event from set and let the API re-solve from the plan it names.
 *
 * `base_job_id` is not optional in practice: the service takes concurrent requests on one
 * instance, so an event that does not name the plan it means to edit will edit whichever plan
 * happens to be latest. A stale base comes back 409 and is shown rather than retried, because
 * retrying would silently rewrite somebody else's schedule.
 */
export function useSetEvent() {
  const [pending, setPending] = useState<SetEventKind | null>(null)
  const [error, setError] = useState<string | null>(null)

  const publish = useCallback(
    async (
      kind: SetEventKind,
      payload: Record<string, unknown>,
      baseJobId: string | null,
      source: SetEventSource = 'ui',
    ) => {
      setPending(kind)
      setError(null)
      try {
        return await apiFetch<SetEventResponse>('/api/set-events', {
          method: 'POST',
          body: JSON.stringify({ kind, payload, source, base_job_id: baseJobId }),
          timeoutMs: 30_000,
        })
      } catch (caught) {
        setError(
          caught instanceof ApiError
            ? caught.status === 409
              ? 'The plan moved under this event. Solve again and republish.'
              : caught.status === 422
                // The engine's own sentence, which names the id it refused: "cast member 'cZ' is
                // not in the schedule". Printing only the status hid the one useful thing in the
                // response, and a proposal read from a sentence can name an id a button never
                // could, so this is the case that needs the detail most.
                ? detail(caught.body)
                : `The API answered ${caught.status}.`
            : caught instanceof Error
              ? caught.message
              : 'The API could not be reached.',
        )
        return null
      } finally {
        setPending(null)
      }
    },
    [],
  )

  return { publish, pending, error }
}


/** The `detail` out of a FastAPI error body, or the body itself when it is not that shape. */
function detail(body: string): string {
  try {
    const parsed: unknown = JSON.parse(body)
    if (parsed && typeof parsed === 'object' && 'detail' in parsed) {
      const value = (parsed as { detail: unknown }).detail
      if (typeof value === 'string' && value.trim()) return `The event was refused: ${value}`
    }
  } catch {
    // Not JSON. Fall through to the status line rather than printing a page of HTML.
  }
  return 'The API answered 422 and the event was refused.'
}
