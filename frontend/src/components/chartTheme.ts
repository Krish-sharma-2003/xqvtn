import type { CSSProperties } from 'react'

export const chartGridProps = {
  strokeDasharray: '2 2',
  stroke: 'rgba(255, 255, 255, 0.10)',
  vertical: false,
}

export const chartAxisTickProps = {
  fontSize: 11,
  fill: '#b6c2d6',
}

export const chartAxisLineProps = {
  axisLine: false,
  tickLine: false,
}

export const chartMargin = {
  top: 18,
  right: 20,
  bottom: 12,
  left: 72,
}

export const chartMarginWithBottomSpace = {
  top: 18,
  right: 20,
  bottom: 26,
  left: 72,
}

export const chartTooltipStyle: CSSProperties = {
  background: 'rgba(255, 255, 255, 0.18)',
  border: '1px solid rgba(255, 255, 255, 0.22)',
  borderRadius: 10,
  color: '#f8fafc',
  padding: '10px 12px',
  fontSize: 12.5,
  minWidth: 210,
  boxShadow: '0 8px 24px rgba(0, 0, 0, 0.35)',
  backdropFilter: 'blur(12px)',
  WebkitBackdropFilter: 'blur(12px)',
}

export const chartLegendWrapperStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 10,
  padding: '6px 18px 16px',
}

export const getChartMargin = (bottom = 12) => ({
  top: 18,
  right: 20,
  bottom,
  left: 72,
})
