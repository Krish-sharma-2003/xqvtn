import { CardHeader } from './CardHeader'

interface ChartCardProps {
  title: string
  subtitle?: string
  unitChip?: string
  infoTooltip?: string
  right?: React.ReactNode
  children: React.ReactNode
  className?: string
}

export function ChartCard({ title, subtitle, unitChip, infoTooltip, right, children, className }: ChartCardProps) {
  const classes = ['card', 'card-strong', 'card-animated']
  if (className) classes.push(className)
  return (
    <section className={classes.join(' ')}>
      <CardHeader title={title} subtitle={subtitle} unitChip={unitChip} infoTooltip={infoTooltip} right={right} />
      <div className="chart-panel">{children}</div>
    </section>
  )
}
