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

export interface AccuracyMetrics {
  n: number
  mae: number | null
  rmse: number | null
  bias: number | null
  nmae_pct: number | null
  p50_abs: number | null
  p90_abs: number | null
  p95_abs: number | null
  shortfall_p90: number | null
}

export interface AccuracySummaryResponse {
  cutoff: string
  in_sample: boolean
  metrics: AccuracyMetrics
}

export interface HorizonBucketMetrics {
  bucket_start: number
  bucket_end: number
  metrics: AccuracyMetrics
}

export interface AccuracyByHorizonResponse {
  buckets: HorizonBucketMetrics[]
}

export interface HourOfDayMetrics {
  hour: number
  metrics: AccuracyMetrics
}

export interface AccuracyByHourResponse {
  hours: HourOfDayMetrics[]
}

export interface DailyAccuracyRow {
  day: string
  n: number
  mae: number | null
  bias: number | null
  nmae_pct: number | null
}

export interface AccuracyDailyResponse {
  days: DailyAccuracyRow[]
}

export interface ErrorHistogramBin {
  bin_start: number
  bin_end: number
  count: number
}

export interface AccuracyErrorsResponse {
  bin_width: number
  bins: ErrorHistogramBin[]
}
