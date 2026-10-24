interface KpiCardProps {
  title: string
  value: React.ReactNode
  unit?: string
  sub?: string
  children?: React.ReactNode
}

export function KpiCard({ title, value, unit, sub, children }: KpiCardProps) {
  return (
    <div className="kpi-card card-animated">
      <p className="kpi-title">{title}</p>
      <p className="kpi-value">
        <span className="kpi-anim">{value}</span>
        {unit ? (
          <span className="kpi-unit">{` ${unit}`}</span>
        ) : null}
      </p>
      {sub ? <p className="kpi-sub">{sub}</p> : null}
      {children ? <div className="kpi-extra">{children}</div> : null}
    </div>
  )
}
