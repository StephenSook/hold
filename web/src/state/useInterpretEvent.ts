import { useCallback, useState } from 'react'
import { ApiError, apiFetch } from '@/lib/api'
import type { EventProposal, ScheduleInput } from '@/types/contracts'

/**
 * Read one sentence about what happened on set into one typed event.
 *
 * Nothing is published here. The hook returns a proposal, the panel shows the reading, and a
 * person presses publish. That split is the whole design: interpreting English is a judgement and
 * belongs to a model, while deciding what the change costs is arithmetic over a rule set and
 * belongs to the solver. Putting the model on the second half would make the number unprovable.
 */
export function useInterpretEvent() {
  const [proposal, setProposal] = useState<EventProposal | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [reading, setReading] = useState(false)

  const clear = useCallback(() => {
    setProposal(null)
    setError(null)
  }, [])

  const interpret = useCallback(async (sentence: string, schedule: ScheduleInput) => {
    if (!sentence.trim()) return
    setReading(true)
    setError(null)
    setProposal(null)
    try {
      setProposal(
        await apiFetch<EventProposal>('/api/interpret-event', {
          method: 'POST',
          body: JSON.stringify({ sentence, schedule }),
          timeoutMs: 30_000,
        }),
      )
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.status === 503
            ? 'The agent is not configured on this deployment, so nothing was read and nothing was guessed.'
            : caught.status === 422
              ? 'That is longer than one sentence about one change. A whole call sheet belongs on the import page.'
              : `The API answered ${caught.status}.`
          : 'The API could not be reached.',
      )
    } finally {
      setReading(false)
    }
  }, [])

  return { interpret, clear, proposal, error, reading }
}
