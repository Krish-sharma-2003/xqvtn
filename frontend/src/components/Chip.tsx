interface ChipProps {
  children: React.ReactNode
  title?: string
}

export function Chip({ children, title }: ChipProps) {
  return (
    <span className="chip" data-tip={title ?? ''} aria-label={title ? `${String(children)}. ${title}` : undefined}>
      {children}
    </span>
  )
}
