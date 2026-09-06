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
  /** Signatures already shown, so a replay cannot show the same event twice. */
  seen: string[]
  dropped: boolean
}

const EMPTY: StreamState = { jobId: null, lines: [], seen: [], dropped: false }

/**
 * What makes two deliveries the same event.
 *
 * The stream carries no id, so the signature is the kind plus the rendered line, and every line
 * this hook builds already embeds what distinguishes it: an objective carries its millisecond, a
 * verdict its day and status. Two deliveries that agree on all of that are the same event
 * arriving twice, which is exactly what a replay is.
 */
const signature = (kind: string, text: string): string => `${kind}\u0000${text}`

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

    /**
     * EventSource reconnects on its own and this URL asks for a replay every time, so a reconnect
     * re-delivers the history and appending it duplicated the log after any blip.
     *
     * The first fix cleared the lines on reconnect, on the premise that the replay was about to
     * re-send them. That premise is false in the one case this hook exists for: the bus is in
     * process, so after an instance swap the new process replays nothing, and clearing would
     * discard the only remaining copy of the log while reporting the stream as connected.
     *
     * Skipping what has already been shown loses nothing in either case.
     */
    const add = (kind: string, text: string) => {
      if (!current) return
      const key = signature(kind, text)
      setStored((prev) => {
        const base = prev.jobId === jobId ? prev : { jobId, lines: [], seen: [], dropped: false }
        if (base.seen.includes(key)) return base
        return {
          ...base,
          lines: [...base.lines.slice(-40), { at: Date.now(), kind, text }],
          seen: [...base.seen.slice(-200), key],
        }
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
          // The inner kind is part of the line, not only the outer one. It tells the reader which
          // event this was, and it keeps two echoes on one job from sharing a signature and being
          // deduplicated as if they were the same delivery.
          const what = typeof parsed.kind === 'string' ? parsed.kind : kind
          const change = typeof parsed.change === 'string' ? `, ${parsed.change}` : ''
          add(kind, `${what}${change}${parsed.transport ? ` over ${parsed.transport}` : ''}`)
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
      setStored((prev) => ({ ...(prev.jobId === jobId ? prev : { jobId, lines: [], seen: [] }), dropped: true }))
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
