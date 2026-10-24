import type { ReactNode } from 'react'

interface CardHeaderProps {
  title: string
  subtitle?: string
  unitChip?: string
  infoTooltip?: string
  right?: ReactNode
  icon?: ReactNode
}

export function CardHeader({ title, subtitle, unitChip, infoTooltip, right, icon }: CardHeaderProps) {
  return (
    <header className="card-header">
      <div className="card-header-left">
        <span className="card-header-accent" aria-hidden="true" />
        <div className="card-header-text">
          <div className="card-header-title-row">
            {icon ? <span className="card-header-icon">{icon}</span> : null}
            <h2 className="card-header-title">{title}</h2>
            {unitChip ? (
              <span
                className="unit-chip"
                tabIndex={0}
                role="note"
                aria-label={`${unitChip} = megawatts`}
                title="MW = megawatts"
              >
                {unitChip}
              </span>
            ) : null}
            {infoTooltip ? (
              <button
                className="info-button"
                type="button"
                aria-label="More information"
                title={infoTooltip}
              >
                <span aria-hidden="true">(i)</span>
              </button>
            ) : null}
          </div>
          {subtitle ? <p className="card-header-subtitle">{subtitle}</p> : null}
        </div>
      </div>
      {right ? <div className="card-header-right">{right}</div> : null}
    </header>
  )
}
