import { useCallback, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Camera, Check, FileUp, TriangleAlert } from 'lucide-react'
import { ActionButton } from '@/components/Action'
import { extractDocument } from '@/lib/extract'
import { putImported } from '@/state/handoff'
import { ApiError } from '@/lib/api'
import { eighths } from '@/lib/format'
import type { ExtractResult } from '@/types/contracts'

/**
 * Import a call sheet, a one-line schedule or a plain-English note.
 *
 * The agent turns the document into typed constraints or into questions. Nothing solves until a
 * person confirms: an extraction is a proposal, and the model refuses to guess anything the
 * document does not state, so the questions are the useful answer as often as the schedule is.
 */
type Phase = 'idle' | 'reading' | 'ready' | 'failed'

export function ImportPage() {
  const navigate = useNavigate()
  const [phase, setPhase] = useState<Phase>('idle')
  const [result, setResult] = useState<ExtractResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [confirmed, setConfirmed] = useState(false)
  const [note, setNote] = useState('')
  const [fileName, setFileName] = useState<string | null>(null)
  const camera = useRef<HTMLInputElement>(null)

  const send = useCallback(async (input: { text?: string; file?: File }) => {
    setPhase('reading')
    setError(null)
    setResult(null)
    setConfirmed(false)
    setFileName(input.file?.name ?? null)
    try {
      setResult(await extractDocument(input))
      setPhase('ready')
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.status === 503
            ? 'Extraction is not configured on this deployment, so nothing was read and nothing was guessed.'
            : `The API answered ${caught.status}. ${caught.body.slice(0, 180)}`
          : caught instanceof Error
            ? caught.message
            : 'The API could not be reached.',
      )
      setPhase('failed')
    }
  }, [])

  const schedule = result?.schedule

  return (
    <div className="mx-auto max-w-[52rem] px-5 py-10 sm:px-8 sm:py-14">
      <p className="script-label text-11 text-bone-faint">Import</p>
      <h1 className="display-wide mt-3 text-28 text-bone sm:text-36">Read a document into the board</h1>
      <p className="mt-4 max-w-[58ch] text-16 text-bone-dim">
        A call sheet, a one-line schedule, or a note in plain English. The agent returns typed
        constraints or the questions it needs answered, and refuses to guess anything the document
        does not state. Nothing solves until you confirm.
      </p>

      <div className="mt-8 space-y-6 border border-rail p-6">
        <div>
          <label htmlFor="import-text" className="script-label block text-11 text-bone-faint">
            A note, in plain English
          </label>
          <textarea
            id="import-text"
            data-testid="import-text"
            value={note}
            onChange={(event) => setNote(event.target.value)}
            rows={3}
            placeholder="Scene 4 moves to Thursday. The minor is not available on the 8th."
            className="script mt-3 w-full resize-y border border-edge bg-board-2 px-3 py-2.5 text-13 text-bone placeholder:text-bone-faint focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bone"
          />
        </div>

        <div>
          <label htmlFor="import-file" className="script-label block text-11 text-bone-faint">
            Or a document
          </label>
          <input
            id="import-file"
            data-testid="import-file"
            type="file"
            accept=".png,.jpg,.jpeg,.pdf,.txt,text/plain,image/*,application/pdf"
            onChange={(event) => {
              const file = event.target.files?.[0]
              if (file) void send({ text: note, file })
            }}
            className="script mt-3 block w-full cursor-pointer text-12 text-bone-dim file:mr-4 file:h-11 file:cursor-pointer file:border file:border-edge file:bg-transparent file:px-4 file:text-11 file:tracking-[0.08em] file:text-bone file:uppercase hover:file:border-bone"
          />
          <p className="script mt-3 text-11 text-bone-faint">
            PNG, JPG, PDF or plain text. Sample documents are in the repository at
            data/demo/samples.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <ActionButton
            onClick={() => void send({ text: note })}
            disabled={phase === 'reading' || note.trim().length === 0}
            icon={<FileUp className="size-3.5" />}
            data-testid="import-submit"
          >
            {phase === 'reading' ? 'Reading' : 'Read it'}
          </ActionButton>

          {/* On a phone this opens the camera. It is the file input with a capture hint, which is
              a real scan on a real device in the installed app, with no native plugin. */}
          <ActionButton
            onClick={() => camera.current?.click()}
            variant="quiet"
            icon={<Camera className="size-3.5" />}
          >
            Scan a call sheet
          </ActionButton>
          <input
            ref={camera}
            data-testid="import-camera"
            type="file"
            accept="image/*"
            capture="environment"
            className="sr-only"
            tabIndex={-1}
            onChange={(event) => {
              const file = event.target.files?.[0]
              if (file) void send({ text: note, file })
            }}
          />
        </div>

        {/* No Capacitor branch. Capacitor is not in this build, and a runtime check for a plugin
            that cannot be present would put its name in shipped code while docs/claims-audit.md
            says the name appears nowhere. What ships is the browser capture, which is a real scan
            on a real phone in the installed app. */}
        <p className="script text-11 text-bone-faint" data-testid="scan-capability">
          Scan opens the camera on a phone, in the browser and in the installed app. On a desktop
          browser it picks a file instead. There is no native document-scanner plugin in this
          build.
        </p>
      </div>

      {phase === 'reading' && (
        <p role="status" className="script mt-6 flex items-center gap-3 text-12 text-bone-dim">
          <FileUp className="size-4" aria-hidden="true" />
          Reading {fileName ?? 'the note'}
        </p>
      )}

      {phase === 'failed' && (
        <p
          role="status"
          data-testid="extract-error"
          className="script mt-6 flex items-start gap-3 border border-flag/60 px-4 py-3 text-12 text-bone"
        >
          <TriangleAlert className="mt-0.5 size-4 shrink-0 text-flag" aria-hidden="true" />
          <span>{error}</span>
        </p>
      )}

      {result && (
        <section className="mt-8 border border-rail" data-testid="extract-result">
          <header className="script flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-rail bg-board-3 px-5 py-3 text-12">
            <span className="font-bold tracking-[0.1em]">
              {result.status === 'ok' ? 'READ' : 'NEEDS CLARIFICATION'}
            </span>
            {fileName && <span className="text-bone-dim">{fileName}</span>}
          </header>

          {result.notes && <p className="border-b border-rail px-5 py-4 text-14 text-bone-dim">{result.notes}</p>}

          {result.status === 'needs_clarification' && (
            <div className="px-5 py-5">
              <p className="script-label text-11 text-bone-faint">What the document does not state</p>
              <ul className="mt-4 space-y-3">
                {result.questions.map((question) => (
                  <li key={question} className="flex gap-3 text-14 text-bone">
                    <span aria-hidden="true" className="mt-2.5 h-px w-4 shrink-0 bg-rail" />
                    <span>{question}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {schedule && (
            <div className="px-5 py-5">
              <dl className="script grid grid-cols-2 gap-x-8 gap-y-4 text-12 sm:grid-cols-4">
                <Pair label="SCENES" value={String(schedule.scenes.length)} />
                <Pair label="CAST" value={String(schedule.cast.length)} />
                <Pair label="DAYS" value={String(schedule.days.length)} />
                <Pair
                  label="PAGES"
                  value={eighths(schedule.scenes.reduce((sum, scene) => sum + scene.pages_eighths, 0))}
                />
              </dl>
              {schedule.constructed && (
                <p className="script mt-5 text-11 text-bone-faint">
                  This schedule is flagged constructed. It is demo data, not a real production.
                </p>
              )}
              <div className="mt-6 flex flex-wrap items-center gap-4">
                <ActionButton
                  onClick={() => {
                    // The confirmation is the handoff. This button used to set a flag and print a
                    // sentence, and the schedule the agent had just read was discarded.
                    putImported(schedule)
                    setConfirmed(true)
                    navigate('/board')
                  }}
                  disabled={confirmed}
                  icon={<Check className="size-3.5" />}
                  data-testid="import-confirm"
                >
                  {confirmed ? 'Confirmed' : 'Confirm and solve'}
                </ActionButton>
                {confirmed && (
                  <p className="script text-11 text-bone-dim" data-testid="import-confirmed">
                    Confirmed. Opening the board.
                  </p>
                )}
              </div>
            </div>
          )}
        </section>
      )}
    </div>
  )
}

function Pair({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-10 tracking-[0.12em] text-bone-faint">{label}</dt>
      <dd className="mt-0.5 tabular-nums text-bone">{value}</dd>
    </div>
  )
}
