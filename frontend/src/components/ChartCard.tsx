interface ChartCardProps {
  title: string
  children: React.ReactNode
}

export function ChartCard({ title, children }: ChartCardProps) {
  return (
    <section className="card card-strong">
      <h2 className="section-title">{title}</h2>
      <div className="chart-wrap">{children}</div>
    </section>
  )
}
