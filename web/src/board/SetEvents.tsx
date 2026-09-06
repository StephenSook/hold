import { useState } from 'react'
import { CloudRain, HelpCircle, Sparkles, UserX, Scissors } from 'lucide-react'
import { ActionButton } from '@/components/Action'
import { useInterpretEvent } from '@/state/useInterpretEvent'
import type { EventProposal, ScheduleInput, SetEventKind, SetEventSource } from '@/types/contracts'
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

/** The proposal, in the words the board uses, so a person confirms a reading and not a JSON blob. */
function describe(proposal: EventProposal): string {
  const day = proposal.day_index === null ? null : `day ${proposal.day_index + 1}`
  if (proposal.kind === 'actor_late') return [`cast ${proposal.cast_id ?? '?'}`, day].filter(Boolean).join(', ')
  if (proposal.kind === 'scene_dropped') return `scene ${proposal.scene_id ?? '?'}`
  return day ?? 'a day this board does not have'
}

export function SetEvents({
  onPublish,
  pending,
  error,
  disabled,
  lines,
  streamState,
  jobId,
  transport,
  schedule,
}: {
  onPublish: (kind: SetEventKind, payload: Record<string, unknown>, source: SetEventSource) => void
  pending: SetEventKind | null
  error: string | null
  disabled: boolean
  lines: StreamLine[]
  streamState: 'idle' | 'open' | 'closed'
  jobId: string | null
  transport: string | null
  schedule: ScheduleInput
}) {
  const [sentence, setSentence] = useState('')
  const agent = useInterpretEvent()

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
            onClick={() => onPublish(event.kind, event.payload, 'ui')}
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

      {/*
        The same three events, reached by saying what happened rather than by knowing which button
        maps to it. The model's only job is turning the sentence into one of those three typed
        events; what the change costs is still decided by the solver, through the identical path
        the buttons above use. Nothing is applied until the reading below is confirmed, which is
        why the proposal is safe to be wrong: a person reads it, and the engine refuses an id that
        does not exist even if they do not.
      */}
      <div className="border-t border-rail px-5 py-5" data-testid="event-interpreter">
        <form
          onSubmit={(event) => {
            event.preventDefault()
            void agent.interpret(sentence, schedule)
          }}
          className="flex flex-wrap items-center gap-3"
        >
          <label htmlFor="event-sentence" className="sr-only">
            What happened on set, in plain English
          </label>
          <input
            id="event-sentence"
            value={sentence}
            onChange={(event) => setSentence(event.target.value)}
            placeholder="B is out on Thursday"
            className="script min-w-0 flex-1 border border-edge bg-board px-3 py-2.5 text-12 text-bone placeholder:text-bone-faint focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bone"
            data-testid="event-sentence"
          />
          <ActionButton
            type="submit"
            variant="quiet"
            disabled={agent.reading || !sentence.trim()}
            icon={<Sparkles className="size-3.5" />}
            data-testid="event-interpret"
          >
            {agent.reading ? 'Reading' : 'Read it'}
          </ActionButton>
        </form>

        {agent.error && (
          <p role="status" className="script mt-4 border border-flag/60 px-4 py-3 text-12 text-bone" data-testid="interpret-error">
            {agent.error}
          </p>
        )}

        {agent.proposal?.status === 'needs_clarification' && (
          <div className="mt-4 border border-rail px-4 py-4" data-testid="interpret-questions">
            <p className="script-label flex items-center gap-2 text-11 text-bone-faint">
              <HelpCircle className="size-3.5" aria-hidden="true" />
              It will not guess
            </p>
            <ul className="mt-3 space-y-2">
              {agent.proposal.questions.map((question) => (
                <li key={question} className="flex gap-3 text-13 text-bone">
                  <span aria-hidden="true" className="mt-2 h-px w-4 shrink-0 bg-rail" />
                  <span>{question}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {agent.proposal?.status === 'ok' && agent.proposal.kind && (
          <div className="mt-4 border border-rail px-4 py-4" data-testid="interpret-proposal">
            <p className="script-label text-11 text-bone-faint">It read that as</p>
            <p className="mt-2 text-14 text-bone">{agent.proposal.reading}</p>
            <p className="script mt-3 text-11 text-bone-dim" data-testid="interpret-typed">
              {agent.proposal.kind}   {describe(agent.proposal)}
            </p>
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <ActionButton
                disabled={disabled || pending !== null}
                onClick={() => {
                  const { kind, payload } = agent.proposal ?? {}
                  if (!kind || !payload) return
                  onPublish(kind, payload, 'agent')
                  agent.clear()
                  setSentence('')
                }}
                data-testid="interpret-publish"
              >
                Publish this event
              </ActionButton>
              <button
                type="button"
                onClick={agent.clear}
                className="script cursor-pointer text-11 text-bone-faint underline decoration-rail underline-offset-4 transition-colors hover:text-bone"
                data-testid="interpret-discard"
              >
                That is not what happened
              </button>
            </div>
          </div>
        )}
      </div>

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
