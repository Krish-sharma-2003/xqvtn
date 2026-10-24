import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Line,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { TooltipPayload } from 'recharts'
import type {
  AccuracyByHourResponse,
  AccuracyByHorizonResponse,
  AccuracyDailyResponse,
  AccuracyErrorsResponse,
  AccuracySummaryResponse,
} from '../types'
import { createAccuracyClient } from '../api'
import { ChartCard } from '../components/ChartCard'
import { CardHeader } from '../components/CardHeader'
import { ErrorState } from '../components/ErrorState'
import { Loading } from '../components/Loading'
import { yAxisProps } from '../components/chartAxis'
import {
  chartAxisLineProps,
  chartAxisTickProps,
  chartGridProps,
  getChartMargin,
} from '../components/chartTheme'

const DEFAULT_CUTOFF = '09:00'

function fmtMw(v: number | null | undefined): string {
  return v === null || v === undefined ? '–' : `${v.toFixed(1)} MW`
}

function fmtPct(v: number | null | undefined): string {
  return v === null || v === undefined ? '–' : `${v.toFixed(1)} %`
}

const client = createAccuracyClient()

export default function Accuracy({ onSelectDay }: { onSelectDay: (day: string) => void }) {
  const [cutoff, setCutoff] = useState(DEFAULT_CUTOFF)
  const [summary, setSummary] = useState<AccuracySummaryResponse | null>(null)
  const [byHorizon, setByHorizon] = useState<AccuracyByHorizonResponse | null>(null)
  const [byHour, setByHour] = useState<AccuracyByHourResponse | null>(null)
  const [daily, setDaily] = useState<AccuracyDailyResponse | null>(null)
  const [errors, setErrors] = useState<AccuracyErrorsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const abortRef = useRef<AbortController | null>(null)

  const load = useCallback(async (nextCutoff: string) => {
    setLoading(true)
    setError(null)
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    try {
      const [s, h, hr, d, e] = await Promise.all([
        client.fetchSummary(nextCutoff, controller.signal),
        client.fetchByHorizon(controller.signal),
        client.fetchByHour(nextCutoff, controller.signal),
        client.fetchDaily(nextCutoff, controller.signal),
        client.fetchErrors(nextCutoff, controller.signal),
      ])
      if (controller.signal.aborted) return
      setSummary(s)
      setByHorizon(h)
      setByHour(hr)
      setDaily(d)
      setErrors(e)
    } catch (err) {
      if (controller.signal.aborted) return
      setError(err instanceof Error ? err.message : 'Failed to load accuracy data')
    } finally {
      if (!controller.signal.aborted) setLoading(false)
    }
  }, [])

  useEffect(() => {
    load(cutoff)
    return () => {
      abortRef.current?.abort()
    }
  }, [cutoff, load])

  const handleCutoff = (v: string) => setCutoff(v)

  const worstDays = (daily?.days ?? [])
    .filter((d) => d.mae !== null)
    .slice()
    .sort((a, b) => (b.mae ?? 0) - (a.mae ?? 0))
    .slice(0, 5)

  const horizonBuckets = byHorizon?.buckets ?? []
  const decisionBuckets = horizonBuckets.filter((b) => b.bucket_start >= 12 && b.bucket_end <= 42)
  const bestBucket = decisionBuckets.length
    ? decisionBuckets.reduce((a, b) => ((a.metrics.mae ?? Infinity) < (b.metrics.mae ?? Infinity) ? a : b))
    : null
  const worstBucket = decisionBuckets.length
    ? decisionBuckets.reduce((a, b) => ((a.metrics.mae ?? -Infinity) > (b.metrics.mae ?? -Infinity) ? a : b))
    : null

  const biasWords = (() => {
    const b = summary?.metrics.bias
    if (b === null || b === undefined) return ''
    const abs = Math.abs(b).toFixed(1)
    return b > 0
      ? `Forecast is on average ${abs} MW higher than actual`
      : b < 0
      ? `Forecast is on average ${abs} MW lower than actual`
      : 'Forecast is on average equal to actual'
  })()

  const m = summary?.metrics

  return (
    <div className="accuracy-page">
      <section className="card card-strong card-animated">
        <CardHeader title="Accuracy" subtitle="In-sample statistics over all January 2026 target days (decision-time forecasts)" />
        <div className="controls">
          <div className="field">
            <label className="label">Cutoff (Europe/London)</label>
            <div className="control-row">
              <select value={cutoff} onChange={(e) => handleCutoff(e.target.value)}>
                {Array.from({ length: 48 }, (_, i) => {
                  const h = String(Math.floor(i / 2)).padStart(2, '0')
                  const mm = i % 2 === 0 ? '00' : '30'
                  const v = `${h}:${mm}`
                  return <option key={v} value={v}>{v}</option>
                })}
              </select>
            </div>
          </div>
        </div>
      </section>

      {loading && !summary ? (
        <Loading />
      ) : error ? (
        <ErrorState message={error} onRetry={() => load(cutoff)} />
      ) : (
        <>
          <div className="metric-grid">
            <section className="card card-strong metric-card">
              <CardHeader title="MAE" unitChip="MW" infoTooltip="Mean absolute error: average magnitude of forecast error." />
              <div className="metric-value">{fmtMw(m?.mae ?? null)}</div>
            </section>
            <section className="card card-strong metric-card">
              <CardHeader title="RMSE" unitChip="MW" infoTooltip="Root mean squared error: penalises large errors." />
              <div className="metric-value">{fmtMw(m?.rmse ?? null)}</div>
            </section>
            <section className="card card-strong metric-card">
              <CardHeader title="Bias" unitChip="MW" infoTooltip="Mean signed error (forecast - actual); positive = over-forecast = shortfall risk." />
              <div className="metric-value">{fmtMw(m?.bias ?? null)}</div>
              <p className="metric-note">{biasWords}</p>
              <p className="metric-note metric-note-dim">error = forecast - actual; positive = over-forecast = shortfall risk</p>
            </section>
            <section className="card card-strong metric-card">
              <CardHeader title="nMAE" unitChip="%" infoTooltip="MAE divided by mean actual, in percent." />
              <div className="metric-value">{fmtPct(m?.nmae_pct ?? null)}</div>
            </section>
            <section className="card card-strong metric-card">
              <CardHeader title="P90 |error|" unitChip="MW" infoTooltip="90th percentile of absolute error." />
              <div className="metric-value">{fmtMw(m?.p90_abs ?? null)}</div>
            </section>
            <section className="card card-strong metric-card">
              <CardHeader title="P95 |error|" unitChip="MW" infoTooltip="95th percentile of absolute error." />
              <div className="metric-value">{fmtMw(m?.p95_abs ?? null)}</div>
            </section>
          </div>

          <ChartCard
            title="Error by forecast horizon"
            subtitle="MAE bars per 6h bucket plus bias line"
            unitChip="MW"
            infoTooltip="Horizon = startTime - publishTime, grouped into 6h buckets."
          >
            <ResponsiveContainer width="100%" height={300}>
              <ComposedChart data={horizonBuckets.map((b) => ({ label: `${b.bucket_start}-${b.bucket_end} h`, mae: b.metrics.mae, bias: b.metrics.bias, n: b.metrics.n, rmse: b.metrics.rmse, p90: b.metrics.p90_abs }))} margin={getChartMargin(12)}>
                <CartesianGrid {...chartGridProps} />
                <XAxis dataKey="label" type="category" tick={chartAxisTickProps} {...chartAxisLineProps} />
                <YAxis type="number" {...yAxisProps} />
                <ReferenceArea x1="12-18 h" x2="36-42 h" fill="rgba(255,255,255,0.06)" stroke="rgba(255,255,255,0.12)" label={{ value: 'typical day-ahead decision horizon', position: 'top', fill: '#94a3b8', fontSize: 11 }} />
                <Bar dataKey="mae" fill="#22d3ee" radius={[4, 4, 0, 0]} />
                <Line dataKey="bias" stroke="#a78bfa" strokeWidth={2} dot={{ r: 3 }} />
                <Tooltip content={HorizonTooltip} />
              </ComposedChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="Error by hour of day" subtitle="MAE bars and bias line per hour 0-23 UTC" unitChip="MW">
            <ResponsiveContainer width="100%" height={300}>
              <ComposedChart data={(byHour?.hours ?? []).map((h) => ({ hour: h.hour, mae: h.metrics.mae, bias: h.metrics.bias, n: h.metrics.n, rmse: h.metrics.rmse, p90: h.metrics.p90_abs }))} margin={getChartMargin(12)}>
                <CartesianGrid {...chartGridProps} />
                <XAxis dataKey="hour" type="number" ticks={[...Array(24).keys()]} tickFormatter={(v) => String(v).padStart(2, '0')} tick={chartAxisTickProps} {...chartAxisLineProps} />
                <YAxis type="number" {...yAxisProps} />
                <Bar dataKey="mae" fill="#22d3ee" radius={[4, 4, 0, 0]} />
                <Line dataKey="bias" stroke="#a78bfa" strokeWidth={2} dot={false} />
                <Tooltip content={HourTooltip} />
              </ComposedChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="Error distribution" subtitle="Histogram of signed error in MW" unitChip="MW">
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={(errors?.bins ?? []).map((b) => ({ label: `${b.bin_start.toFixed(0)}`, start: b.bin_start, end: b.bin_end, count: b.count, center: (b.bin_start + b.bin_end) / 2 }))} margin={getChartMargin(12)}>
                <CartesianGrid {...chartGridProps} />
                <XAxis dataKey="label" type="category" tick={chartAxisTickProps} {...chartAxisLineProps} />
                <YAxis type="number" {...yAxisProps} />
                <ReferenceLine x="0" stroke="rgba(255,255,255,0.4)" />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {(errors?.bins ?? []).map((b, i) => {
                    const center = (b.bin_start + b.bin_end) / 2
                    const fill = center < 0 ? '#f87171' : '#22d3ee'
                    return <Cell key={i} fill={fill} />
                  })}
                </Bar>
                <Tooltip content={ErrorTooltip} cursor={{ fill: 'rgba(255,255,255,0.06)' }} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          <section className="card card-strong card-animated">
            <CardHeader title="How to use this in a purchase decision" />
            <div className="decision-use">
              <p>P90 over-forecast is {fmtMw(m?.shortfall_p90 ?? null)}: keep at least this much backup.</p>
              <p>
                Best horizon bucket (among 12-42 h ahead): {bestBucket ? `${bestBucket.bucket_start}-${bestBucket.bucket_end} h (MAE ${bestBucket.metrics.mae?.toFixed(1)} MW)` : '–'}, worst: {worstBucket ? `${worstBucket.bucket_start}-${worstBucket.bucket_end} h (MAE ${worstBucket.metrics.mae?.toFixed(1)} MW)` : '–'}.
              </p>
              <p>Overall MAE is {fmtMw(m?.mae ?? null)} (nMAE {fmtPct(m?.nmae_pct ?? null)}); bias {fmtMw(m?.bias ?? null)}.</p>
            </div>
          </section>

          <section className="card card-strong card-animated table-wrap">
            <CardHeader title="Worst days" subtitle="Top 5 days by MAE" unitChip="MW" />
            <table>
              <thead>
                <tr>
                  <th>Day</th>
                  <th className="num">MAE (MW)</th>
                  <th className="num">Bias (MW)</th>
                  <th className="num">nMAE (%)</th>
                </tr>
              </thead>
              <tbody>
                {worstDays.length === 0 ? (
                  <tr><td colSpan={4} className="empty">No daily data.</td></tr>
                ) : (
                  worstDays.map((d) => (
                    <tr key={d.day} className="table-row-clickable" onClick={() => onSelectDay(d.day)}>
                      <td>{d.day}</td>
                      <td className="num">{d.mae?.toFixed(1) ?? '–'}</td>
                      <td className="num">{d.bias?.toFixed(1) ?? '–'}</td>
                      <td className="num">{d.nmae_pct?.toFixed(1) ?? '–'}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
            {worstDays.length === 5 && worstDays.every((d) => d.mae !== null && d.bias !== null && Math.abs((d.bias as number) - (d.mae as number)) < 1e-6) && (
              <p style={{ margin: '8px 0 0', fontSize: 12, color: 'var(--text-muted)' }}>
                Bias equals MAE on these days: the forecast was too high all day.
              </p>
            )}
          </section>
        </>
      )}
    </div>
  )
}

function HorizonTooltip({ active, payload }: { active: boolean; payload: TooltipPayload | null }) {
  if (!active || !payload || payload.length === 0) return null
  const raw = payload[0]?.payload as { label: string; n: number; mae: number | null; rmse: number | null; bias: number | null; p90: number | null } | undefined
  if (!raw) return null
  return (
    <div className="tooltip">
      <div className="tooltip-label">{raw.label}</div>
      <div className="tooltip-row"><span className="key">n</span><span className="val">{raw.n}</span></div>
      <div className="tooltip-row"><span className="key">MAE</span><span className="val">{raw.mae?.toFixed(1) ?? '–'} MW</span></div>
      <div className="tooltip-row"><span className="key">RMSE</span><span className="val">{raw.rmse?.toFixed(1) ?? '–'} MW</span></div>
      <div className="tooltip-row"><span className="key">Bias</span><span className="val">{raw.bias?.toFixed(1) ?? '–'} MW</span></div>
      <div className="tooltip-row"><span className="key">P90 |err|</span><span className="val">{raw.p90?.toFixed(1) ?? '–'} MW</span></div>
    </div>
  )
}

function HourTooltip({ active, payload }: { active: boolean; payload: TooltipPayload | null }) {
  if (!active || !payload || payload.length === 0) return null
  const raw = payload[0]?.payload as { hour: number; n: number; mae: number | null; rmse: number | null; bias: number | null; p90: number | null } | undefined
  if (!raw) return null
  return (
    <div className="tooltip">
      <div className="tooltip-label">Hour {String(raw.hour).padStart(2, '0')}:00 UTC</div>
      <div className="tooltip-row"><span className="key">n</span><span className="val">{raw.n}</span></div>
      <div className="tooltip-row"><span className="key">MAE</span><span className="val">{raw.mae?.toFixed(1) ?? '–'} MW</span></div>
      <div className="tooltip-row"><span className="key">RMSE</span><span className="val">{raw.rmse?.toFixed(1) ?? '–'} MW</span></div>
      <div className="tooltip-row"><span className="key">Bias</span><span className="val">{raw.bias?.toFixed(1) ?? '–'} MW</span></div>
      <div className="tooltip-row"><span className="key">P90 |err|</span><span className="val">{raw.p90?.toFixed(1) ?? '–'} MW</span></div>
    </div>
  )
}

function ErrorTooltip({ active, payload }: { active: boolean; payload: TooltipPayload | null }) {
  if (!active || !payload || payload.length === 0) return null
  const raw = payload[0]?.payload as { start: number; end: number; count: number } | undefined
  if (!raw) return null
  return (
    <div className="tooltip">
      <div className="tooltip-label">{raw.start.toFixed(0)} to {raw.end.toFixed(0)} MW</div>
      <div className="tooltip-row"><span className="key">Count</span><span className="val">{raw.count}</span></div>
    </div>
  )
}
