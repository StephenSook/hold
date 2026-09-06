import { CloudRain, UserX, Scissors } from 'lucide-react'
import { ActionButton } from '@/components/Action'
import type { SetEventKind } from '@/types/contracts'
import type { StreamLine } from '@/state/useEventStream'

/**
 * What happens on set, and what the plan does about it.
 *
 * Each of these is a real event the API accepts, and each one re-solves from the named plan
 * rather than patching the one on screen, which is why the answer carries a new job id. The
 * stream below is the service's own account of that, not a narration of it.
 */
const EVENTS: { kind: SetEventKind; label: string; icon: typeof UserX; payload: Record<string, unknown> }[] = [
  { kind: 'scene_dropped', label: 'Scene dropped', icon: Scissors, payload: { scene_id: 's6' } },
  { kind: 'actor_late', label: 'Actor late', icon: UserX, payload: { cast_id: 'cM', minutes: 120 } },
  { kind: 'weather_cover', label: 'Weather cover', icon: CloudRain, payload: { day: 3 } },
]

export function SetEvents({
  onPublish,
  pending,
  error,
  disabled,
  lines,
  streamState,
  jobId,
  transport,
}: {
  onPublish: (kind: SetEventKind, payload: Record<string, unknown>) => void
  pending: SetEventKind | null
  error: string | null
  disabled: boolean
  lines: StreamLine[]
  streamState: 'idle' | 'open' | 'closed'
  jobId: string | null
  transport: string | null
}) {
  return (
    <section className="mt-10 border border-rail">
      <header className="script flex flex-wrap items-center justify-between gap-3 border-b border-rail bg-board-3 px-5 py-3 text-11">
        <span className="font-bold tracking-[0.12em]">SOMETHING HAPPENED ON SET</span>
        <span className="text-bone-dim">
          {jobId ? (
            <>
              plan <span data-testid="job-id">{jobId}</span>
              {transport ? ` over ${transport}` : ''}
            </>
          ) : (
            'solve first, then an event has a plan to edit'
          )}
        </span>
      </header>

      <div className="flex flex-wrap gap-3 px-5 py-5">
        {EVENTS.map((event) => (
          <ActionButton
            key={event.kind}
            variant="quiet"
            disabled={disabled || pending !== null}
            onClick={() => onPublish(event.kind, event.payload)}
            icon={<event.icon className="size-3.5" />}
            data-testid={`set-event-${event.kind}`}
          >
            {pending === event.kind ? 'Publishing' : event.label}
          </ActionButton>
        ))}
      </div>

      {error && (
        <p role="status" className="script border-t border-rail px-5 py-3 text-12 text-bone">
          {error}
        </p>
      )}

      <div className="border-t border-rail px-5 py-4">
        <p className="script-label text-10 text-bone-faint">
          The stream {streamState === 'open' ? 'is connected' : streamState === 'closed' ? 'closed' : 'is not open'}
        </p>
        <ul className="script mt-3 max-h-40 space-y-1 overflow-y-auto text-11 text-bone-dim" data-testid="event-log">
          {lines.length === 0 && <li className="text-bone-faint">Nothing has come through yet.</li>}
          {lines.map((line) => (
            <li key={`${line.at}-${line.text}`} className="tabular-nums">
              <span className="text-bone-faint">
                {new Date(line.at).toLocaleTimeString('en-GB', { hour12: false })}{' '}
              </span>
              {line.text}
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
