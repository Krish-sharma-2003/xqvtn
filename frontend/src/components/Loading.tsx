export function Loading() {
  return (
    <div className="loader">
      <div className="skeleton circle skeleton-circle" />
      <div className="skeleton shimmer skeleton-bar" style={{ width: '52%' }} />
      <div className="skeleton shimmer skeleton-bar" style={{ width: '70%' }} />
      <div className="skeleton shimmer skeleton-bar" style={{ width: '40%' }} />
      <div className="skeleton shimmer skeleton-bar" style={{ width: '85%' }} />
      <p className="muted">Loading decision data&hellip;</p>
    </div>
  )
}
