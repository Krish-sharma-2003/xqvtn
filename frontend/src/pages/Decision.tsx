import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  LineChart,
  ReferenceLine,
  Scatter,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipPayload,
} from 'recharts'
import type { CutoffSensitivityResponse, DecisionResponse } from '../types'
import { createDecisionClient } from '../api'
import { ChartCard } from '../components/ChartCard'
import { CardHeader } from '../components/CardHeader'
import { yAxisProps } from '../components/chartAxis'
import { Chip } from '../components/Chip'
import { ErrorState } from '../components/ErrorState'
import { KpiCard } from '../components/KpiCard'
import { Loading } from '../components/Loading'
import { chartAxisLineProps, chartAxisTickProps, chartGridProps, getChartMargin } from '../components/chartTheme'
import { Clock, Gauge, TrendingDown } from 'lucide-react'

const MIN_DAY = '2026-01-02'
const MAX_DAY = '2026-02-01'
const DEFAULT_CUTOFF = '09:00'
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

interface ChartPoint {
  hour: number
  forecast: number | null
  conservative: number | null
  actual: number | null
  publishTime: string | null
  horizon_h: number | null
}

interface SensitivityPoint {
  cutoff: string
  mean_forecast: number | null
  publishTime: string | null
}

type SeriesKey = 'forecast' | 'conservative' | 'buffer' | 'actual'

const SERIES: ReadonlyArray<{ key: SeriesKey; label: string; swatch: string }> = [
  { key: 'forecast', label: 'Forecast', swatch: 'swatch-solid' },
  { key: 'conservative', label: 'Conservative', swatch: 'swatch-dashed' },
  { key: 'buffer', label: 'Risk buffer', swatch: 'swatch-fill' },
  { key: 'actual', label: 'Actual', swatch: 'swatch-dotted' },
]

function fmtTime(iso: string | null): string {
  return iso ? iso.slice(11, 16) : '–'
}

function fmtDay(iso: string): string {
  const d = new Date(`${iso}T00:00:00Z`)
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`
}

function fmtUtc(iso: string | null): string {
  if (!iso) return '–'
  const d = new Date(iso)
  return `${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')} UTC`
}

function fmtUtcDay(iso: string | null): string {
  if (!iso) return '–'
  const d = new Date(iso)
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`
}

function fmtMw(value: number | null): string {
  return value === null ? '–' : `${value.toFixed(1)} MW`
}

function fmtHorizon(value: number | null): string {
  return value === null ? '–' : `${value.toFixed(1)} h`
}

function addMinutes(time: string, minutes: number): string {
  const [hh, mm] = time.split(':').map(Number)
  let total = hh * 60 + mm + minutes
  total = ((total % 1440) + 1440) % 1440
  return `${String(Math.floor(total / 60)).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`
}

function shiftDay(day: string, delta: number): string {
  const d = new Date(`${day}T00:00:00Z`)
  d.setUTCDate(d.getUTCDate() + delta)
  return d.toISOString().slice(0, 10)
}

function clampDay(day: string): string {
  if (day < MIN_DAY) return MIN_DAY
  if (day > MAX_DAY) return MAX_DAY
  return day
}

function useWindowWidth(): number {
  const [width, setWidth] = useState(typeof window === 'undefined' ? 1024 : window.innerWidth)
  useEffect(() => {
    const onResize = () => setWidth(window.innerWidth)
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])
  return width
}


function firstTooltipPoint(payload: TooltipPayload): ChartPoint | null {
  const raw = payload[0]?.payload ?? null
  if (!raw || typeof raw !== 'object') return null
  return raw as ChartPoint
}

const client = createDecisionClient()

function ChartTooltip({
  active,
  payload,
}: {
  active: boolean
  payload: TooltipPayload | null
}) {
  if (!active || !payload || payload.length === 0) return null
  const point = firstTooltipPoint(payload)
  if (!point) return null
  const buffer =
    point.forecast !== null && point.conservative !== null
      ? point.forecast - point.conservative
      : null
  return (
    <div className="tooltip">
      <div className="tooltip-label">
        Hour {String(point.hour).padStart(2, '0')}:00 UTC
      </div>
      <div className="tooltip-row">
        <span className="key">Forecast</span>
        <span className="val">{fmtMw(point.forecast)}</span>
      </div>
      <div className="tooltip-row">
        <span className="key">Conservative</span>
        <span className="val">{fmtMw(point.conservative)}</span>
      </div>
      <div className="tooltip-row">
        <span className="key">Risk buffer</span>
        <span className="val">{fmtMw(buffer)}</span>
      </div>
      {point.actual !== null && (
        <div className="tooltip-row">
          <span className="key">Actual</span>
          <span className="val">{fmtMw(point.actual)}</span>
        </div>
      )}
      <div className="tooltip-row" style={{ borderTop: '1px solid var(--border)', marginTop: 6, paddingTop: 6, fontSize: 11.5 }}>
        <span className="key">Publish time</span>
        <span className="val">{fmtTime(point.publishTime)}</span>
      </div>
      <div className="tooltip-row" style={{ fontSize: 11.5 }}>
        <span className="key">Horizon</span>
        <span className="val">{fmtHorizon(point.horizon_h)}</span>
      </div>
    </div>
  )
}

function SensitivityTooltip({
  active,
  payload,
}: {
  active: boolean
  payload: TooltipPayload | null
}) {
  if (!active || !payload || payload.length === 0) return null
  const raw = payload[0]?.payload ?? null
  if (!raw || typeof raw !== 'object') return null
  const point = raw as SensitivityPoint
  return (
    <div className="tooltip">
      <div className="tooltip-label">{point.cutoff}</div>
      <div className="tooltip-row">
        <span className="key">Mean forecast</span>
        <span className="val">{fmtMw(point.mean_forecast)}</span>
      </div>
      <div className="tooltip-row" style={{ fontSize: 11.5 }}>
        <span className="key">Publish time</span>
        <span className="val">{fmtTime(point.publishTime)}</span>
      </div>
    </div>
  )
}

function SensitivityChart({
  data,
  onPick,
  selectedCutoff,
}: {
  data: SensitivityPoint[]
  onPick: (cutoff: string) => void
  selectedCutoff: string
}) {
  const width = useWindowWidth()
  return (
    <ResponsiveContainer width="100%" height={width < 640 ? 220 : 200}>
      <LineChart data={data} margin={{ top: 10, right: 16, bottom: 28, left: 72 }}>
        <CartesianGrid {...chartGridProps} />
        <XAxis
          dataKey="cutoff"
          type="category"
          tick={chartAxisTickProps}
          {...chartAxisLineProps}
        />
        <YAxis type="number" {...yAxisProps} domain={([dataMin, dataMax]: readonly [number, number]) => [Math.floor((dataMin - 50) / 50) * 50, Math.ceil((dataMax + 50) / 50) * 50]} />
        <ReferenceLine x={selectedCutoff} stroke="var(--accent)" strokeDasharray="4 4" label={{ value: 'selected', position: 'top', fill: 'var(--accent)', fontSize: 11 }} />
        <Line
          dataKey="mean_forecast"
          stroke="#22d3ee"
          strokeWidth={2}
          dot={({ cx, cy, payload }: any) => {
            const isSel = payload?.cutoff === selectedCutoff
            return (
              <circle
                cx={cx}
                cy={cy}
                r={isSel ? 5 : 3}
                fill="#22d3ee"
                stroke="#070a14"
                strokeWidth={isSel ? 2 : 1}
                className={isSel ? 'selected-cutoff-dot' : undefined}
              />
            )
          }}
          activeDot={{ r: 6 }}
          onClick={(event: unknown) => {
            const picked = event as { payload?: { cutoff?: string } | null }
            const c = picked.payload?.cutoff
            if (typeof c === 'string') onPick(c)
          }}
        />
        <Tooltip content={SensitivityTooltip} />
      </LineChart>
    </ResponsiveContainer>
  )
}

function SeriesLegend({
  hidden,
  onToggle,
  showActual,
  onToggleActual,
}: {
  hidden: Set<SeriesKey>
  onToggle: (key: SeriesKey) => void
  showActual: boolean
  onToggleActual: () => void
}) {
  return (
    <div className="legend">
      {SERIES.map((item) => {
        const disabled = item.key === 'actual' && !showActual
        const active = !hidden.has(item.key) && !disabled
        return (
          <button
            key={item.key}
            className={`legend-item ${active ? 'active' : ''} ${disabled ? 'disabled' : ''}`}
            onClick={() => {
              if (disabled) return
              if (item.key === 'actual') onToggleActual()
              else onToggle(item.key)
            }}
          >
            <span className={`swatch ${item.swatch}`} />
            {item.label}
          </button>
        )
      })}
    </div>
  )
}

export default function Decision({ initialDay }: { initialDay?: string } = {}) {
  const width = useWindowWidth()
  const [day, setDay] = useState(initialDay && initialDay >= MIN_DAY && initialDay <= MAX_DAY ? initialDay : MIN_DAY)
  const [cutoff, setCutoff] = useState(DEFAULT_CUTOFF)
  const [showActual, setShowActual] = useState(false)
  const [hoveredHour, setHoveredHour] = useState<number | null>(null)
  const [howOpen, setHowOpen] = useState(false)
  const [hidden, setHidden] = useState<Set<SeriesKey>>(new Set())
  const [data, setData] = useState<DecisionResponse | null>(null)
  const [sensitivity, setSensitivity] = useState<CutoffSensitivityResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const abortRef = useRef<AbortController | null>(null)

  const isHidden = (key: SeriesKey): boolean => hidden.has(key)

  const toggleSeries = (key: SeriesKey): void => {
    setHidden((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  const requestIdRef = useRef(0)

  const loadDecision = useCallback(
    async (nextDay: string, nextCutoff: string) => {
      const thisId = ++requestIdRef.current
      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller
      setLoading(true)
      setError(null)
      try {
        const [decision, sens] = await Promise.all([
          client.fetchDecision(nextDay, nextCutoff, controller.signal),
          client.fetchCutoffSensitivity(nextDay, controller.signal),
        ])
        if (controller.signal.aborted || thisId !== requestIdRef.current) return
        setData(decision)
        setSensitivity(sens)
        setError(null)
      } catch (err) {
        if (controller.signal.aborted || thisId !== requestIdRef.current) return
        setData(null)
        setSensitivity(null)
        setError(err instanceof Error ? err.message : 'Failed to load decision data')
      } finally {
        if (!controller.signal.aborted && thisId === requestIdRef.current) setLoading(false)
      }
    },
    [],
  )

  useEffect(() => {
    loadDecision(day, cutoff)
    return () => {
      abortRef.current?.abort()
    }
  }, [day, cutoff, loadDecision])

  const points = data?.points ?? []
  const summary = data?.summary
  const chartData = useMemo(
    () =>
      points.map((p, index) => ({
        hour: index,
        forecast: p.forecast,
        conservative: p.conservative,
        actual: p.actual,
        publishTime: p.publishTime,
        horizon_h: p.horizon_h,
      })),
    [points],
  )

  const horizons = points.map((p) => p.horizon_h).filter((v): v is number => v !== null)
  const horizonRange =
    horizons.length > 0
      ? `${Math.min(...horizons).toFixed(1)} h – ${Math.max(...horizons).toFixed(1)} h`
      : '–'

  const sensData = useMemo(
    () =>
      (sensitivity?.cutoffs ?? []).map((c) => ({
        cutoff: c.cutoff,
        mean_forecast: c.mean_forecast,
        publishTime: c.publishTime,
      })),
    [sensitivity],
  )

  const ticks = useMemo(() => [...Array(24).keys()], [])

  const handleDay = (next: string): void => {
    const fixed = clampDay(next)
    setDay(fixed)
  }

  const handleCutoff = (next: string): void => {
    setCutoff(next)
  }

  const handleCutoffStep = (delta: number): void => {
    const next = addMinutes(cutoff, delta)
    setCutoff(next)
  }

  const handleSensitivityPick = (nextCutoff: string): void => {
    setCutoff(nextCutoff)
  }

  const conservativeMean = summary && summary.forecast_mean !== null && summary.buffer_mean !== null ? (summary.forecast_mean ?? 0) - (summary.buffer_mean ?? 0) : null
  const coveredHours = showActual ? points.filter((p) => p.actual !== null && p.conservative !== null && (p.actual as number) >= (p.conservative as number)).length : 0

  return (
    <div className="decision">
      <section className="card">
        <div style={{ padding: '14px 18px' }}>
          <p style={{ margin: 0, fontWeight: 600 }}>
            Plan for ~{conservativeMean !== null ? conservativeMean.toFixed(0) : '–'} MW of wind (mean conservative forecast) and hold ~{summary?.buffer_mean?.toFixed(0) ?? '–'} MW backup (mean buffer). Forecast published {fmtTime(points[0]?.publishTime ?? null)} UTC, {points[0]?.horizon_h?.toFixed(1) ?? '–'}-{points[points.length-1]?.horizon_h?.toFixed(1) ?? '–'} h ahead.
          </p>
          <button aria-expanded={howOpen} onClick={() => setHowOpen((v) => !v)} style={{ marginTop: 8, background: 'none', border: 'none', color: 'var(--accent)', cursor: 'pointer', padding: 0 }}>
            How to read this
          </button>
          {howOpen && (
            <ul style={{ margin: '6px 0 0 18px', color: 'var(--text-muted)', fontSize: 13 }}>
              <li>Forecast: latest published wind forecast for each hour.</li>
              <li>Conservative: forecast reduced by the historical shortfall percentile.</li>
              <li>Risk buffer: forecast minus conservative, the volume to back up.</li>
            </ul>
          )}
        </div>
      </section>
      <section className="card">
        <div className="controls">
          <div className="field">
            <label className="label">Target day</label>
            <div className="control-row">
              <button className="button button-icon" onClick={() => handleDay(shiftDay(day, -1))} disabled={day <= MIN_DAY}>
                &lsaquo;
              </button>
              <input type="date" min={MIN_DAY} max={MAX_DAY} value={day} onChange={(event) => handleDay(event.target.value)} />
              <button className="button button-icon" onClick={() => handleDay(shiftDay(day, 1))} disabled={day >= MAX_DAY}>
                &rsaquo;
              </button>
            </div>
          </div>
          <div className="field">
            <label className="label">Cutoff (Europe/London)</label>
            <div className="control-row">
              <button className="button button-icon" onClick={() => handleCutoffStep(-30)}>
                &minus;30&prime;
              </button>
              <select value={cutoff} onChange={(event) => handleCutoff(event.target.value)}>
                {Array.from({ length: 48 }, (_, i) => {
                  const h = String(Math.floor(i / 2)).padStart(2, '0')
                  const m = i % 2 === 0 ? '00' : '30'
                  const v = `${h}:${m}`
                  return <option key={v} value={v}>{v}</option>
                })}
              </select>
              <button className="button button-icon" onClick={() => handleCutoffStep(30)}>
                +30&prime;
              </button>
            </div>
          </div>
          <div className="field">
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text)' }}>
              <button
                type="button"
                role="switch"
                aria-checked={showActual}
                aria-label="Hindsight actuals"
                onClick={() => setShowActual((v) => !v)}
                onKeyDown={(e) => { if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); setShowActual((v) => !v) } }}
                className="hindsight-switch"
                style={{ width: 34, height: 18, borderRadius: 9, background: showActual ? 'var(--accent)' : 'rgba(255,255,255,0.15)', position: 'relative', transition: 'background .2s', border: 'none', cursor: 'pointer', padding: 0 }}
              >
                <span style={{ position: 'absolute', top: 2, left: showActual ? 18 : 2, width: 14, height: 14, borderRadius: '50%', background: '#fff', transition: 'left .2s' }} />
              </button>
              <span>Hindsight actuals: {showActual ? 'Shown' : 'Hidden'}</span>
            </div>
          </div>
        </div>
      </section>

      {error ? (
        <ErrorState message={error} onRetry={() => loadDecision(day, cutoff)} />
      ) : loading && !data ? (
        <Loading />
      ) : (
        <div style={loading ? { opacity: 0.5, pointerEvents: 'none' } : undefined}>
        <>
          {points.length === 0 ? (
            <div className="empty">No decision data available for {fmtDay(day)}.</div>
          ) : (
            <>
              <ChartCard
                title={`Decision forecast - ${fmtDay(data?.day ?? day)}`}
                subtitle="Latest forecast available at the selected cutoff"
                unitChip="MW"
                right={loading && data ? <span className="chip">Updating…</span> : undefined}
              >
                <ResponsiveContainer width="100%" height={width < 640 ? 240 : 300}>
                  <ComposedChart data={chartData} margin={getChartMargin(12)}>
                    <CartesianGrid {...chartGridProps} />
                    <XAxis
                      dataKey="hour"
                      type="number"
                      ticks={ticks}
                      tickFormatter={(value: unknown) => `${String(value).padStart(2, '0')}:00`}
                      tick={chartAxisTickProps}
                      {...chartAxisLineProps}
                      tickMargin={10}
                    />
                    <YAxis type="number" {...yAxisProps} domain={([dataMin, dataMax]: readonly [number, number]) => [Math.floor((dataMin - 100) / 100) * 100, Math.ceil((dataMax + 100) / 100) * 100]} />
                    {!isHidden('buffer') && (
                      <Area type="monotone" dataKey="forecast" fill="#22d3ee" fillOpacity={0.18} stroke="none" legendType="none" />
                    )}
                    {!isHidden('buffer') && !isHidden('conservative') && (
                      <Area type="monotone" dataKey="conservative" fill="rgba(255, 255, 255, 0.18)" fillOpacity={1} stroke="none" legendType="none" />
                    )}
                    {!isHidden('forecast') && (
                      <Line type="monotone" dataKey="forecast" stroke="#22d3ee" strokeWidth={2} dot={false} />
                    )}
                    {!isHidden('conservative') && (
                      <Line type="monotone" dataKey="conservative" stroke="#a78bfa" strokeWidth={2} strokeDasharray="5 5" dot={false} />
                    )}
                    {showActual && !isHidden('actual') && (
                      <Line type="monotone" dataKey="actual" stroke="#f472b6" strokeWidth={2} strokeDasharray="2 4" dot={false} />
                    )}
                    {hoveredHour !== null && <ReferenceLine x={hoveredHour} stroke='rgba(255,255,255,0.4)' />}
                    {showActual && <Scatter data={chartData.filter((p) => p.actual !== null && p.conservative !== null && (p.actual as number) < (p.conservative as number))} fill='#f87171' />}
                    <Tooltip content={ChartTooltip} />
                  </ComposedChart>
                </ResponsiveContainer>
                <SeriesLegend
                  hidden={hidden}
                  onToggle={toggleSeries}
                  showActual={showActual}
                  onToggleActual={() => setShowActual((prev) => !prev)}
                />
              </ChartCard>

              <div className="kpi-grid kpi-grid-full">
                <KpiCard
                  title="Publish time used"
                  value={fmtTime(points[0]?.publishTime ?? null)}
                  sub={horizonRange}
                  icon={<Clock size={16} strokeWidth={1.75} />}
                />
                <KpiCard title="Mean forecast" value={summary?.forecast_mean?.toFixed(1) ?? '–'} unit="MW" icon={<Gauge size={16} strokeWidth={1.75} />} />
                <KpiCard title="Mean buffer" value={summary?.buffer_mean?.toFixed(1) ?? '–'} unit="MW" icon={<TrendingDown size={16} strokeWidth={1.75} />} />
                {showActual && (
                  <div className="kpi-card">
                    <div className="kpi-title">Covered hours</div>
                    <div className="kpi-value">{coveredHours} / 24</div>
                    {summary?.in_sample ? <div className="kpi-sub"><span className="in-sample-badge">in-sample</span></div> : null}
                  </div>
                )}
                <KpiCard
                  title="Cutoff (UTC)"
                  value={fmtUtc(summary?.cutoff_utc ?? null)}
                  sub={fmtUtcDay(summary?.cutoff_utc ?? null)}
                >
                  {summary?.in_sample ? <Chip title="Fewer than three usable target days precede this decision day, so the error statistics fall back to all-January data. Treat the buffer as less reliable for this day.">in-sample</Chip> : null}
                </KpiCard>
              </div>

              <ChartCard title="Cutoff sensitivity" subtitle="How the forecast changes if the gate closes earlier or later" unitChip="MW" right={loading && data ? <span className="chip">Updating…</span> : undefined}>
                {sensData.length === 0 ? (
                  <div className="empty">No sensitivity data available for {fmtDay(day)}.</div>
                ) : (
                  <>
                    <SensitivityChart data={sensData} onPick={handleSensitivityPick} selectedCutoff={cutoff} />
                    <table style={{ marginTop: 10, width: '100%', fontSize: 12 }}>
                      <thead><tr><th>Cutoff</th><th>Publish time</th><th>Mean forecast</th><th>Delta vs selected</th></tr></thead>
                      <tbody>
                        {sensData.map((c) => {
                          const selectedMean = summary?.forecast_mean ?? sensData.find((x) => x.cutoff === cutoff)?.mean_forecast ?? null
                          const delta = (c.mean_forecast ?? 0) - (selectedMean ?? 0)
                          return (
                            <tr key={c.cutoff} onClick={() => handleSensitivityPick(c.cutoff)} style={{ cursor: 'pointer' }}>
                              <td>{c.cutoff}</td>
                              <td>{fmtTime(c.publishTime)}</td>
                              <td>{fmtMw(c.mean_forecast)}</td>
                              <td style={{ color: delta > 0 ? 'var(--accent)' : delta < 0 ? 'var(--danger)' : 'inherit' }}>
                                {delta > 0 ? '▲' : delta < 0 ? '▼' : ''} {delta.toFixed(1)} MW
                              </td>
                            </tr>
                          )
                        })}
                      <tr style={{ fontWeight: 700 }}>
                        <td>{cutoff} (selected)</td>
                        <td>{fmtTime(points[0]?.publishTime ?? null)}</td>
                        <td>{fmtMw(summary?.forecast_mean ?? null)}</td>
                        <td>0.0 MW</td>
                      </tr>
                      </tbody>
                    </table>
                  </>
                )}
              </ChartCard>

              <section className="card card-strong card-animated table-wrap">
                <CardHeader title="24-hour table" unitChip="MW" />
                <table>
                  <thead>
                    <tr>
                      <th>Hour (UTC)</th>
                      <th className="num">Forecast (MW)</th>
                      <th className="num">Conservative (MW)</th>
                      <th className="num">Buffer (MW)</th>
                      <th className="num">Actual (MW)</th>
                      <th>Shortfall</th>
                      <th>Publish time</th>
                      <th className="num">Horizon (h)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {points.map((p, index) => {
                      const isShortfall = showActual && p.actual !== null && p.conservative !== null && (p.actual as number) < (p.conservative as number)
                      return (
                        <tr key={String(index)} onMouseEnter={() => setHoveredHour(index)} onMouseLeave={() => setHoveredHour(null)} className="table-row-clickable" style={isShortfall ? { background: 'rgba(248,113,113,0.12)' } : undefined}>
                          <td>{String(index).padStart(2, '0')}:00</td>
                          <td className="num">{fmtMw(p.forecast)}</td>
                          <td className="num">{fmtMw(p.conservative)}</td>
                          <td className="num">{fmtMw(p.buffer)}</td>
                          <td className="num">{fmtMw(p.actual)}</td>
                          <td>{isShortfall ? <span className="shortfall-badge">shortfall</span> : null}</td>
                          <td>{fmtTime(p.publishTime)}</td>
                          <td className="num">{fmtHorizon(p.horizon_h)}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </section>
            </>
          )}
        </>
        </div>
      )}
      <footer className="page-footer">Data: Elexon BMRS (FUELHH, WINDFOR), national wind, January 2026 decisions. Times in UTC.</footer>
    </div>
  )
}