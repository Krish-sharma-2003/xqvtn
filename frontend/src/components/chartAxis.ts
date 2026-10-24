export const yAxisProps = {
  width: 72,
  tickMargin: 6,
  tick: { fontSize: 11, fill: '#b6c2d6' },
  axisLine: false,
  tickLine: false,
  tickFormatter: (value: number) => {
    const s = value.toLocaleString('en-US')
    return s.replace(/,/g, '\u00A0')
  },
}
