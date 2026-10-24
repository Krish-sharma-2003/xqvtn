import type {
  AccuracyByHourResponse,
  AccuracyByHorizonResponse,
  AccuracyDailyResponse,
  AccuracyErrorsResponse,
  AccuracySummaryResponse,
  CutoffSensitivityResponse,
  DecisionResponse,
} from './types'

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

export interface AccuracyClient {
  fetchSummary(cutoff: string, signal: AbortSignal): Promise<AccuracySummaryResponse>
  fetchByHorizon(signal: AbortSignal): Promise<AccuracyByHorizonResponse>
  fetchByHour(cutoff: string, signal: AbortSignal): Promise<AccuracyByHourResponse>
  fetchDaily(cutoff: string, signal: AbortSignal): Promise<AccuracyDailyResponse>
  fetchErrors(cutoff: string, signal: AbortSignal): Promise<AccuracyErrorsResponse>
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

export function createAccuracyClient(
  baseURL: string = import.meta.env.VITE_API_BASE ?? '',
): AccuracyClient {
  async function get<T>(path: string, signal?: AbortSignal): Promise<T> {
    const response = await fetch(`${baseURL}${path}`, { signal })
    if (!response.ok) {
      throw new ApiError(response.status, response.statusText)
    }
    return (await response.json()) as T
  }

  return {
    fetchSummary: (cutoff: string, signal: AbortSignal) =>
      get<AccuracySummaryResponse>(
        `/api/accuracy/summary?cutoff=${encodeURIComponent(cutoff)}`,
        signal,
      ),
    fetchByHorizon: (signal: AbortSignal) =>
      get<AccuracyByHorizonResponse>(`/api/accuracy/by-horizon`, signal),
    fetchByHour: (cutoff: string, signal: AbortSignal) =>
      get<AccuracyByHourResponse>(
        `/api/accuracy/by-hour?cutoff=${encodeURIComponent(cutoff)}`,
        signal,
      ),
    fetchDaily: (cutoff: string, signal: AbortSignal) =>
      get<AccuracyDailyResponse>(
        `/api/accuracy/daily?cutoff=${encodeURIComponent(cutoff)}`,
        signal,
      ),
    fetchErrors: (cutoff: string, signal: AbortSignal) =>
      get<AccuracyErrorsResponse>(
        `/api/accuracy/errors?cutoff=${encodeURIComponent(cutoff)}`,
        signal,
      ),
  }
}
