import { useCallback, useEffect, useRef, useState } from 'react'
import { eventsUrl } from '@/lib/api'

export interface StreamLine {
  at: number
  kind: string
  text: string
}

interface StreamState {
  /** The job these lines belong to. Keying the state to the job is what removes the need for a
   *  reset effect: a different job simply has no lines yet, rather than the old ones being
   *  cleared afterwards. */
  jobId: string | null
  lines: StreamLine[]
  dropped: boolean
}

const EMPTY: StreamState = { jobId: null, lines: [], dropped: false }

/**
 * The server-sent stream for one job.
 *
 * EventSource closes for good on an HTTP error, which a host's proxy will produce during an
 * instance swap, so a dropped stream is reported rather than silently left dead. The lines are
 * what the service said, not a paraphrase: the transport it names is the transport that carried
 * the event.
 */
export function useEventStream(jobId: string | null, enabled = true) {
  const [stored, setStored] = useState<StreamState>(EMPTY)
  const source = useRef<EventSource | null>(null)
  const live = Boolean(jobId) && enabled && typeof EventSource !== 'undefined'

  // Everything the caller reads is derived from the arguments and the stored job, so a stale job's
  // lines can never be shown against a new one.
  const current = stored.jobId === jobId ? stored : EMPTY
  const state: 'idle' | 'open' | 'closed' = !live ? 'idle' : current.dropped ? 'closed' : 'open'

  useEffect(() => {
    source.current?.close()
    source.current = null
    if (!live || !jobId) return

    const stream = new EventSource(eventsUrl(jobId, true, 60))
    source.current = stream

    // A message already queued when the job changed will still run this handler with the old
    // job's closure. Without this guard its updater wins, storage flips back to the old job, and
    // the new job's replayed lines disappear from a log that looks perfectly healthy.
    let current = true

    const add = (kind: string, text: string) => {
      if (!current) return
      setStored((prev) => {
        const base = prev.jobId === jobId ? prev : { jobId, lines: [], dropped: false }
        return { ...base, lines: [...base.lines.slice(-40), { at: Date.now(), kind, text }] }
      })
    }

    const onMessage = (event: MessageEvent<string>) => {
      try {
        const parsed = JSON.parse(event.data) as Record<string, unknown>
        const kind = String(parsed.event ?? parsed.kind ?? 'message')
        if (kind === 'objective') {
          add(kind, `objective ${parsed.value} bound ${parsed.bound} at ${parsed.t_ms} ms`)
        } else if (kind === 'verdict') {
          const verdict = parsed.verdict as { day?: number; status?: string } | undefined
          add(kind, `day ${Number(verdict?.day ?? 0) + 1} ${verdict?.status ?? ''}`)
        } else {
          add(kind, `${kind}${parsed.transport ? ` over ${parsed.transport}` : ''}`)
        }
      } catch {
        add('message', event.data.slice(0, 120))
      }
    }

    stream.onmessage = onMessage
    for (const named of ['objective', 'verdict', 'set-event']) {
      stream.addEventListener(named, onMessage as EventListener)
    }
    // EventSource retries by itself, so an error is not necessarily the end. Reporting the drop
    // and then clearing it on reconnect is the honest pair: an earlier version set dropped and
    // never cleared it, so a stream that recovered kept saying it had closed while new lines
    // arrived underneath the label.
    stream.onopen = () => {
      if (!current) return
      setStored((prev) => (prev.jobId === jobId && prev.dropped ? { ...prev, dropped: false } : prev))
    }

    stream.onerror = () => {
      if (!current) return
      setStored((prev) => ({ ...(prev.jobId === jobId ? prev : { jobId, lines: [] }), dropped: true }))
      // A closed stream that is also reported closed. Leaving it open to retry while the label
      // says closed is the combination that lies in both directions at once.
      if (stream.readyState === EventSource.CLOSED) {
        source.current = null
      }
    }

    return () => {
      current = false
      stream.close()
      source.current = null
    }
  }, [jobId, live])

  const clear = useCallback(() => setStored(EMPTY), [])

  return { lines: current.lines, state, clear }
}
