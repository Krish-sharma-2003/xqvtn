interface KpiCardProps {
  title: string
  value: React.ReactNode
  unit?: string
  sub?: string
}

export function KpiCard({ title, value, unit, sub }: KpiCardProps) {
  return (
    <div className="kpi-card">
      <p className="kpi-title">{title}</p>
      <p className="kpi-value">
        {value}
        {unit ? (
          <span className="kpi-unit">{` ${unit}`}</span>
        ) : null}
      </p>
      {sub ? <p className="kpi-sub">{sub}</p> : null}
    </div>
  )
}
