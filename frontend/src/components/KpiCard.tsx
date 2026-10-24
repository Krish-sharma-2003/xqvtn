import React from 'react'

interface KpiCardProps {
  title: string
  value: React.ReactNode
  unit?: string
  sub?: string
  icon?: React.ReactNode
  children?: React.ReactNode
}

export function KpiCard({ title, value, unit, sub, icon, children }: KpiCardProps) {
  return (
    <div className="kpi-card card-animated">
      <p className="kpi-title">
        {icon ? <span className="kpi-icon">{icon}</span> : null}
        {title}
      </p>
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
