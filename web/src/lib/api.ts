/**
 * One place that decides where the API is.
 *
 * The web build talks to a relative /api, because the same Cloud Run service serves the built
 * app and the routes. The native shells load from file:// or capacitor://, where a relative
 * path resolves to the bundle, so they set VITE_API_BASE to the Cloud Run origin at build
 * time. PLAN.md, Shared Contracts, "API base and CORS".
 */
const RAW_BASE = (import.meta.env.VITE_API_BASE ?? '').trim()

/** The configured base with any trailing slash removed, or '' for the relative case. */
export const API_BASE = RAW_BASE.replace(/\/+$/, '')

export function apiUrl(path: string): string {
  const suffix = path.startsWith('/') ? path : `/${path}`
  return `${API_BASE}${suffix}`
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly body: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export interface ApiOptions extends RequestInit {
  /** Milliseconds before the request is aborted. Cloud Run cold starts are the reason. */
  timeoutMs?: number
}

export async function apiFetch<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const { timeoutMs = 20_000, ...init } = options
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const response = await fetch(apiUrl(path), {
      ...init,
      signal: init.signal ?? controller.signal,
      headers: {
        Accept: 'application/json',
        ...(init.body ? { 'Content-Type': 'application/json' } : {}),
        ...init.headers,
      },
    })
    if (!response.ok) {
      const body = await response.text().catch(() => '')
      throw new ApiError(`${init.method ?? 'GET'} ${path} answered ${response.status}`, response.status, body)
    }
    return (await response.json()) as T
  } finally {
    clearTimeout(timer)
  }
}

/** The URL an EventSource opens for a job's stream. */
export function eventsUrl(jobId: string, replay = true, limit = 50): string {
  const params = new URLSearchParams({ job_id: jobId, replay: String(replay), limit: String(limit) })
  return apiUrl(`/api/events?${params.toString()}`)
}
