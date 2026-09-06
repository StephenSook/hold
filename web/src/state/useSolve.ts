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

  useEffect(() => {
    cancelled.current = false
    return () => {
      cancelled.current = true
    }
  }, [])

  const reset = useCallback(() => setState(IDLE), [])

  /**
   * Poll a job that already exists to completion.
   *
   * A set event creates a new job rather than patching the current one, so the board adopts that
   * job the same way it adopts its own solve. Sharing the poll means the two paths cannot drift.
   */
  const adopt = useCallback(async (jobId: string) => {
    setState({ ...IDLE, phase: 'solving', jobId })
    try {
      await poll(jobId, cancelled, setState)
    } catch (error) {
      setState({ ...IDLE, phase: 'failed', jobId, error: describe(error) })
    }
  }, [])

  const solve = useCallback(async (schedule: ScheduleInput) => {
    setState({ ...IDLE, phase: 'solving' })
    try {
      const submitted = await apiFetch<{ job_id: string }>('/api/solve', {
        method: 'POST',
        body: JSON.stringify(schedule),
      })
      setState({ ...IDLE, phase: 'solving', jobId: submitted.job_id })
      await poll(submitted.job_id, cancelled, setState)
    } catch (error) {
      setState({ ...IDLE, phase: 'failed', error: describe(error) })
    }
  }, [])

  return { ...state, solve, adopt, reset }
}

function describe(error: unknown): string {
  if (error instanceof ApiError) return `the API answered ${error.status}`
  if (error instanceof Error) return error.message
  return 'the API could not be reached'
}

/** One poll loop, shared by a fresh solve and by a job a set event handed back. */
async function poll(
  jobId: string,
  cancelled: { current: boolean },
  setState: (next: SolveState) => void,
): Promise<void> {
  const started = Date.now()
  for (;;) {
    if (cancelled.current) return
    const job = await apiFetch<JobResponse>(`/api/jobs/${jobId}`)
    if (job.status === 'done' && job.result) {
      setState({
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
      setState({ ...IDLE, phase: 'failed', jobId: job.job_id, error: job.error ?? 'the solve failed' })
      return
    }
    if (Date.now() - started > 120_000) {
      setState({ ...IDLE, phase: 'failed', jobId: job.job_id, error: 'the solve did not finish in 120 seconds' })
      return
    }
    await new Promise((resolve) => setTimeout(resolve, 700))
  }
}
