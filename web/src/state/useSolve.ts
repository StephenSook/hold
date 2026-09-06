import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError, apiFetch } from '@/lib/api'
import type { ScheduleInput, SolveResult } from '@/types/contracts'

interface JobResponse {
  job_id: string
  status: 'queued' | 'running' | 'done' | 'failed'
  result: SolveResult | null
  day_scene_ids: Record<string, string[]>
  error: string | null
  solve_ms: number | null
}

export type SolvePhase = 'idle' | 'solving' | 'done' | 'failed'

export interface SolveState {
  phase: SolvePhase
  jobId: string | null
  result: SolveResult | null
  dayMap: Record<string, string[]> | null
  solveMs: number | null
  error: string | null
}

const IDLE: SolveState = { phase: 'idle', jobId: null, result: null, dayMap: null, solveMs: null, error: null }

/**
 * Run a solve on the API and poll the job to completion.
 *
 * The solver runs on the server on one worker thread, so this polls rather than blocking, and
 * every failure is surfaced rather than swallowed: when the API cannot be reached the caller
 * shows the recorded run and says so on screen, which is the difference between an offline demo
 * and a claim we cannot support.
 */
export function useSolve() {
  const [state, setState] = useState<SolveState>(IDLE)
  const cancelled = useRef(false)
  /**
   * Which operation currently owns the state.
   *
   * An unmount flag alone is not enough. Reset during a solve left the poll running, and it then
   * painted a live result over a board the person had just reset. Two operations can also overlap
   * legitimately: publishing a set event while a solve is still polling gives two loops, and
   * whichever wrote last owned the screen, so the board could show one job's result under
   * another's id. Every write is now stamped, and a stale stamp writes nothing.
   */
  const generation = useRef(0)

  useEffect(() => {
    cancelled.current = false
    return () => {
      cancelled.current = true
    }
  }, [])

  /** Take ownership. Any operation already in flight becomes stale from this moment. */
  const claim = useCallback(() => {
    generation.current += 1
    return generation.current
  }, [])

  /** A setter that only writes while this operation is still the current one. */
  const writerFor = useCallback(
    (token: number) => (next: SolveState) => {
      if (cancelled.current || generation.current !== token) return
      setState(next)
    },
    [],
  )

  const reset = useCallback(() => {
    claim()
    setState(IDLE)
  }, [claim])

  /**
   * Poll a job that already exists to completion.
   *
   * A set event creates a new job rather than patching the current one, so the board adopts that
   * job the same way it adopts its own solve. Sharing the poll means the two paths cannot drift.
   */
  const adopt = useCallback(
    async (jobId: string) => {
      const token = claim()
      const write = writerFor(token)
      write({ ...IDLE, phase: 'solving', jobId })
      try {
        await poll(jobId, write, () => generation.current === token && !cancelled.current)
      } catch (error) {
        write({ ...IDLE, phase: 'failed', jobId, error: describe(error) })
      }
    },
    [claim, writerFor],
  )

  const solve = useCallback(
    async (schedule: ScheduleInput) => {
      const token = claim()
      const write = writerFor(token)
      write({ ...IDLE, phase: 'solving' })
      try {
        const submitted = await apiFetch<{ job_id: string }>('/api/solve', {
          method: 'POST',
          body: JSON.stringify(schedule),
        })
        write({ ...IDLE, phase: 'solving', jobId: submitted.job_id })
        await poll(submitted.job_id, write, () => generation.current === token && !cancelled.current)
      } catch (error) {
        write({ ...IDLE, phase: 'failed', error: describe(error) })
      }
    },
    [claim, writerFor],
  )

  return { ...state, solve, adopt, reset }
}

function describe(error: unknown): string {
  if (error instanceof ApiError) return `the API answered ${error.status}`
  if (error instanceof Error) return error.message
  return 'the API could not be reached'
}

/**
 * One poll loop, shared by a fresh solve and by a job a set event handed back.
 *
 * `owns` is re-read after every await, not only at the top: a request in flight when the operation
 * is superseded would otherwise land, and landing is exactly the problem.
 */
async function poll(
  jobId: string,
  write: (next: SolveState) => void,
  owns: () => boolean,
): Promise<void> {
  const started = Date.now()
  for (;;) {
    if (!owns()) return
    const job = await apiFetch<JobResponse>(`/api/jobs/${jobId}`)
    if (!owns()) return
    if (job.status === 'done' && job.result) {
      write({
        phase: 'done',
        jobId: job.job_id,
        result: job.result,
        dayMap: job.day_scene_ids,
        solveMs: job.solve_ms,
        error: null,
      })
      return
    }
    if (job.status === 'failed') {
      write({ ...IDLE, phase: 'failed', jobId: job.job_id, error: job.error ?? 'the solve failed' })
      return
    }
    if (Date.now() - started > 120_000) {
      write({ ...IDLE, phase: 'failed', jobId: job.job_id, error: 'the solve did not finish in 120 seconds' })
      return
    }
    await new Promise((resolve) => setTimeout(resolve, 700))
  }
}
