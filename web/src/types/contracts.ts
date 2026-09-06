/**
 * Shared contracts, mirrored from api/hold/schemas.py.
 * Owner of the schema is Stephen; this file follows it and never leads it. A change here
 * without a matching change there is a bug, and src/types/contracts.test.ts holds this file
 * to the committed fixtures so the two cannot drift silently.
 */

export type IntExt = 'INT' | 'EXT'
export type DayNight = 'DAY' | 'NIGHT'
export type RateTier = 'low_budget' | 'moderate_low' | 'ultra_low' | 'other'
export type ShootState = 'CA' | 'GA' | 'other'
export type VerdictStatus = 'LEGAL' | 'ILLEGAL' | 'UNDETERMINED'
export type Pass2Status = 'OPTIMAL' | 'FEASIBLE' | 'UNDETERMINED'
export type SetEventKind = 'actor_late' | 'scene_dropped' | 'weather_cover'

export interface Scene {
  id: string
  number: number
  int_ext: IntExt
  day_night: DayNight
  set: string
  pages_eighths: number
  cast_ids: string[]
  location_id: string
}

export interface CastMember {
  id: string
  /** A single letter. The demo data carries letters, never names (PLAN.md D8). */
  letter: string
  /** null for adult cast: no minor rule applies. */
  age: number | null
  /** Two-letter state code, or null when the document did not state one. */
  resident_state: string | null
  day_rate_cents: number
  rate_tier: RateTier
}

export interface ShootDay {
  /** ISO date. */
  date: string
  /** HH:MM:SS. */
  call: string
  wrap: string
  school_day: boolean
  /** The following calendar day is a school day. null means the API derives it. */
  school_night?: boolean | null
}

export interface Constraint {
  type: 'availability' | 'precedence'
  cast_id?: string | null
  scene_id_a?: string | null
  scene_id_b?: string | null
  unavailable_day_indices?: number[] | null
}

export interface ScheduleInput {
  scenes: Scene[]
  cast: CastMember[]
  days: ShootDay[]
  constraints: Constraint[]
  jurisdiction: { shoot_state: ShootState }
  /** true for demo data. Always shown in the interface. */
  constructed: boolean
  overnight_location?: boolean
}

export interface ExtractResult {
  status: 'ok' | 'needs_clarification'
  schedule: ScheduleInput | null
  questions: string[]
  notes: string
}

export interface ViolationRecord {
  rule_id: string
  citation: string
  title: string
  limit: string
  computed: string
  over_by: string
  /** Verbatim sentence from the source. Never paraphrased. */
  quote: string
  source_url: string
  jurisdiction: string
}

export interface WitnessScene {
  id: string
  start: string
  end: string
  cast_ids: string[]
}

export interface WitnessMinor {
  call: string
  dismiss: string
  work_minutes: number
  location_minutes: number
  meal: { start: string; end: string } | null
}

export interface Witness {
  day: number
  date: string
  crew_call: string
  crew_wrap: string
  heuristic?: string
  scenes: WitnessScene[]
  minors: Record<string, WitnessMinor>
}

export interface Verdict {
  status: VerdictStatus
  /** 0-based index into ScheduleInput.days. */
  day: number
  violations: ViolationRecord[]
  /** Rules that each alone make the day impossible. Filled by the solver, not the checker. */
  core_rule_ids: string[]
  witness: Witness | null
  reason: string
}

export interface Pass2Result {
  order: number[]
  status: Pass2Status
  holding_cents: number
  total_cents: number
  bound: number
  hold_days: number
  penalties_cents: number
  reasons: string[]
}

export interface BenchmarkResult {
  instance: string
  published: number
  ours: number
  residual: number
}

export interface SolveResult {
  pass1: Verdict[]
  pass2: Pass2Result
  checker: { agrees: boolean; note?: string }
  benchmark: BenchmarkResult | null
}

/* ---- server-sent events ---- */

export interface ObjectiveEvent {
  event: 'objective'
  job_id: string
  value: number
  bound: number
  t_ms: number
}

export interface VerdictEvent {
  event: 'verdict'
  job_id: string
  verdict: Verdict
}

/**
 * Where a re-solve came from. 'agent' still means a person pressed publish: it records that the
 * typed event was read out of a sentence by the interpreter rather than chosen from a button, and
 * it travels into the streamed line as set-event:<kind>:agent.
 */
export type SetEventSource = 'ui' | 'simulation' | 'agent'

export interface SetEvent {
  event: 'set-event'
  kind: SetEventKind
  payload: Record<string, unknown>
  source: SetEventSource
  base_job_id?: string | null
}

export type HoldEvent = ObjectiveEvent | VerdictEvent | SetEvent

/**
 * One on-set change read from a sentence, for a person to confirm before anything re-solves.
 *
 * This is a proposal and never an action. The model interprets the words; the deterministic
 * `apply_set_event` path decides what the change costs, and only after someone has read the
 * `reading` line and pressed publish.
 */
export interface EventProposal {
  status: 'ok' | 'needs_clarification'
  kind: SetEventKind | null
  /** Filled per kind: actor_late needs both, scene_dropped needs the scene, weather_cover the day. */
  cast_id: string | null
  scene_id: string | null
  /** 0-based, the index the engine wants. A sentence says Thursday; the interpreter converts. */
  day_index: number | null
  /**
   * The publish payload, assembled by the API from the fields above, and empty unless the proposal
   * is complete. The browser publishes it verbatim rather than building its own, so the mapping
   * from named fields to event payload has one definition and cannot drift across the wire.
   */
  payload: Record<string, unknown>
  questions: string[]
  reading: string
}

/* ---- /api/status, read by the judge page ---- */

export interface StatusHeadline {
  hold_days_before: number
  hold_days_after: number
  payroll_removed_usd: number
  illegal_days_before: number
  illegal_days_after: number
  benchmark_matched: string
  solve_ms: number
  adk_eval: unknown
}

export interface StatusRuntime {
  gemini_model: string
  gemini_location: string
  adk_version: string
  ortools_version: string
  confluent: Record<string, unknown>
  mode: string
  extraction: { configured: boolean; reason: string | null }
  invoked_by_this_endpoint: string[]
  note: string
}

export interface StatusResponse {
  computed_at: string
  cache_ttl_s: number
  headline: StatusHeadline
  headline_source: string
  bob_usage: Record<string, unknown>
  facts_generated_at: string
  facts_run_sha: string
  constructed: boolean
  benchmark_matched: string
  benchmark_run_sha: string
  runtime: StatusRuntime
}

/** One tool the agent chose to call, and whether the allowlist let it through. */
export interface ToolCall {
  name: string
  args: Record<string, unknown>
  refused: boolean
  detail: string
}

/**
 * The agent's answer and the trajectory it took.
 *
 * The tool calls are part of the payload, not a log line. An agent that says a day is illegal is
 * worth what the reader can check, and which rule it looked up is the difference between an
 * answer and an assertion.
 */
export interface AskResult {
  answer: string
  tool_calls: ToolCall[]
  fixture: boolean
}
