import { useCallback, useRef, useState } from 'react'
import { Check, FileUp, TriangleAlert } from 'lucide-react'
import { ActionButton } from '@/components/Action'
import { apiUrl } from '@/lib/api'
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
  const [phase, setPhase] = useState<Phase>('idle')
  const [result, setResult] = useState<ExtractResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [confirmed, setConfirmed] = useState(false)
  const [fileName, setFileName] = useState<string | null>(null)
  const input = useRef<HTMLInputElement>(null)

  const send = useCallback(async (file: File) => {
    setPhase('reading')
    setError(null)
    setResult(null)
    setConfirmed(false)
    setFileName(file.name)
    try {
      const body = new FormData()
      body.append('file', file)
      const response = await fetch(apiUrl('/api/extract'), { method: 'POST', body })
      if (!response.ok) {
        const text = await response.text().catch(() => '')
        setError(
          response.status === 503
            ? 'Extraction is not configured on this deployment, so nothing was read.'
            : `The API answered ${response.status}. ${text.slice(0, 180)}`,
        )
        setPhase('failed')
        return
      }
      setResult((await response.json()) as ExtractResult)
      setPhase('ready')
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The API could not be reached.')
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

      <div className="mt-8 border border-rail p-6">
        <label htmlFor="import-file" className="script-label block text-11 text-bone-faint">
          Document
        </label>
        <input
          ref={input}
          id="import-file"
          type="file"
          accept=".png,.jpg,.jpeg,.pdf,.txt,text/plain,image/*,application/pdf"
          onChange={(event) => {
            const file = event.target.files?.[0]
            if (file) void send(file)
          }}
          className="script mt-3 block w-full cursor-pointer text-12 text-bone-dim file:mr-4 file:h-11 file:cursor-pointer file:border file:border-rail file:bg-transparent file:px-4 file:text-11 file:tracking-[0.08em] file:text-bone file:uppercase hover:file:border-bone"
        />
        <p className="script mt-3 text-11 text-bone-faint">
          PNG, JPG, PDF or plain text. Sample documents live in the repository at
          data/demo/samples.
        </p>
      </div>

      {phase === 'reading' && (
        <p role="status" className="script mt-6 flex items-center gap-3 text-12 text-bone-dim">
          <FileUp className="size-4" aria-hidden="true" />
          Reading {fileName}
        </p>
      )}

      {phase === 'failed' && (
        <p
          role="status"
          className="script mt-6 flex items-start gap-3 border border-flag/60 px-4 py-3 text-12 text-bone"
        >
          <TriangleAlert className="mt-0.5 size-4 shrink-0 text-flag" aria-hidden="true" />
          <span>{error}</span>
        </p>
      )}

      {result && (
        <section className="mt-8 border border-rail">
          <header className="script flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-rail bg-board-3 px-5 py-3 text-12">
            <span className="font-bold tracking-[0.1em]">
              {result.status === 'ok' ? 'READ' : 'NEEDS CLARIFICATION'}
            </span>
            {fileName && <span className="opacity-70">{fileName}</span>}
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
                  onClick={() => setConfirmed(true)}
                  disabled={confirmed}
                  icon={<Check className="size-3.5" />}
                >
                  {confirmed ? 'Confirmed' : 'Confirm and solve'}
                </ActionButton>
                {confirmed && (
                  <p className="script text-11 text-bone-dim">
                    Confirmed. Open the board to solve it.
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
