import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'
import type { StatusResponse } from '@/types/contracts'

/**
 * The service's own account of itself. Nothing on this page types a headline number: they are
 * read from here, and this endpoint reads them from a committed file written by a real run.
 */
export function useStatus() {
  return useQuery({
    queryKey: ['status'],
    queryFn: () => apiFetch<StatusResponse>('/api/status', { timeoutMs: 25_000 }),
    staleTime: 10 * 60_000,
  })
}
