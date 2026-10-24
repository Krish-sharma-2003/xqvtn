import type { CutoffSensitivityResponse, DecisionResponse } from './types'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, statusText: string) {
    super(`API request failed with ${status} ${statusText}`)
    this.status = status
    this.name = 'ApiError'
  }
}

export interface DecisionClient {
  fetchDecision(day: string, cutoff: string, signal: AbortSignal): Promise<DecisionResponse>
  fetchCutoffSensitivity(day: string, signal: AbortSignal): Promise<CutoffSensitivityResponse>
}

export function createDecisionClient(
  baseURL: string = import.meta.env.VITE_API_BASE ?? '',
): DecisionClient {
  async function get<T>(path: string, signal?: AbortSignal): Promise<T> {
    const response = await fetch(`${baseURL}${path}`, { signal })
    if (!response.ok) {
      throw new ApiError(response.status, response.statusText)
    }
    return (await response.json()) as T
  }

  return {
    fetchDecision: (day: string, cutoff: string, signal: AbortSignal) =>
      get<DecisionResponse>(
        `/api/decision?day=${encodeURIComponent(day)}&cutoff=${encodeURIComponent(cutoff)}`,
        signal,
      ),
    fetchCutoffSensitivity: (day: string, signal: AbortSignal) =>
      get<CutoffSensitivityResponse>(
        `/api/decision/cutoff-sensitivity?day=${encodeURIComponent(day)}`,
        signal,
      ),
  }
}
