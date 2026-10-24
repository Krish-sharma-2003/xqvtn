export interface HourlyPoint {
  startTime: string
  forecast: number | null
  publishTime: string | null
  horizon_h: number | null
  actual: number | null
  conservative: number | null
  buffer: number | null
}

export interface DecisionSummary {
  forecast_mean: number | null
  forecast_min: number | null
  forecast_max: number | null
  buffer_mean: number | null
  in_sample: boolean
  cutoff_utc: string
}

export interface DecisionResponse {
  day: string
  cutoff: string
  points: HourlyPoint[]
  summary: DecisionSummary
}

export interface CutoffSensitivityPoint {
  cutoff: string
  publishTime: string | null
  mean_forecast: number | null
}

export interface CutoffSensitivityResponse {
  day: string
  cutoffs: CutoffSensitivityPoint[]
}
