import { useCallback, useState } from 'react'
import { MessageSquare, ShieldBan, Wrench } from 'lucide-react'
import { ActionButton } from '@/components/Action'
import { ApiError, apiFetch } from '@/lib/api'
import type { AskResult, ScheduleInput } from '@/types/contracts'

/**
 * Ask the tool-bearing agent about this board.
 *
 * This is the only surface that reaches `root_agent`. Every other route runs the tool-less
 * extraction twin, so until this existed the three tools and the allowlist guarding them were
 * defined, tested and unreachable on the deployed service.
 *
 * The trajectory is shown, not hidden. The point is not that a model produced a sentence: it is
 * which tool it chose, what it passed, and whether the guard let it through. A refused call is
 * rendered as prominently as a successful one, because a guardrail nobody can see doing its job
 * is indistinguishable from one that is not there.
 */
const SUGGESTIONS = [
  'Why can this day not be shot legally?',
  'What is the earliest a minor can be called in Georgia?',
  'Which rule caps a minor at ten hours?',
]

export function AskAgent({ schedule }: { schedule: ScheduleInput }) {
  const [question, setQuestion] = useState('')
  const [result, setResult] = useState<AskResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [asking, setAsking] = useState(false)

  const send = useCallback(
    async (text: string) => {
      if (!text.trim()) return
      setAsking(true)
      setError(null)
      setResult(null)
      try {
        setResult(await apiFetch<AskResult>('/api/ask', {
          method: 'POST',
          body: JSON.stringify({ question: text, schedule }),
          timeoutMs: 60_000,
        }))
      } catch (caught) {
        setError(
          caught instanceof ApiError
            ? caught.status === 503
              ? 'The agent is not configured on this deployment, so nothing was asked and nothing was guessed.'
              : `The API answered ${caught.status}.`
            : 'The API could not be reached.',
        )
      } finally {
        setAsking(false)
      }
    },
    [schedule],
  )

  return (
    <section className="mt-10 border border-rail" data-testid="ask-agent">
      <header className="script flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-rail bg-board-3 px-5 py-3 text-11">
        <MessageSquare className="size-3.5 text-bone-faint" aria-hidden="true" />
        <span className="script-label text-bone">Ask the agent</span>
        <span className="text-bone-faint">
          It reads the rule registry and judges this board with the same checker the solver uses
        </span>
      </header>

      <div className="px-5 py-5">
        <form
          onSubmit={(event) => {
            event.preventDefault()
            void send(question)
          }}
          className="flex flex-wrap items-center gap-3"
        >
          <label htmlFor="ask-input" className="sr-only">
            A question about this board or the rules
          </label>
          <input
            id="ask-input"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Why can day 4 not be shot legally?"
            className="script min-w-0 flex-1 border border-edge bg-board px-3 py-2.5 text-12 text-bone placeholder:text-bone-faint focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bone"
            data-testid="ask-input"
          />
          <ActionButton
            type="submit"
            disabled={asking || !question.trim()}
            icon={<MessageSquare className="size-3.5" />}
            data-testid="ask-submit"
          >
            {asking ? 'Asking' : 'Ask'}
          </ActionButton>
        </form>

        <ul className="mt-4 flex flex-wrap gap-2">
          {SUGGESTIONS.map((text) => (
            <li key={text}>
              <button
                type="button"
                onClick={() => {
                  setQuestion(text)
                  void send(text)
                }}
                disabled={asking}
                className="script cursor-pointer border border-rail px-3 py-1.5 text-11 text-bone-dim transition-colors hover:border-edge hover:text-bone disabled:cursor-not-allowed disabled:opacity-50"
              >
                {text}
              </button>
            </li>
          ))}
        </ul>

        {error && (
          <p className="script mt-5 border border-flag/60 px-4 py-3 text-12 text-bone" data-testid="ask-error">
            {error}
          </p>
        )}

        {result && (
          <div className="mt-6" data-testid="ask-result">
            {result.fixture && (
              <p className="script mb-4 text-11 text-bone-faint">
                This deployment has no model credentials, so this is a recorded answer and says so
                rather than pretending a model was called.
              </p>
            )}
            <p className="max-w-[70ch] text-14 leading-relaxed text-bone">{result.answer}</p>

            {result.tool_calls.length > 0 && (
              <div className="mt-6 border-t border-rail pt-4">
                <p className="script-label text-11 text-bone-faint">What it called to answer that</p>
                <ol className="mt-3 space-y-2">
                  {result.tool_calls.map((call, index) => (
                    <li
                      key={`${call.name}-${index}`}
                      className="script flex flex-wrap items-center gap-x-3 gap-y-1 text-11"
                      data-testid="ask-tool-call"
                    >
                      {call.refused ? (
                        <ShieldBan className="size-3.5 text-flag" aria-hidden="true" />
                      ) : (
                        <Wrench className="size-3.5 text-bone-faint" aria-hidden="true" />
                      )}
                      <span className={call.refused ? 'text-flag' : 'text-bone'}>{call.name}</span>
                      <span className="text-bone-faint">{JSON.stringify(call.args)}</span>
                      {call.refused && <span className="text-flag">refused: {call.detail}</span>}
                    </li>
                  ))}
                </ol>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  )
}
