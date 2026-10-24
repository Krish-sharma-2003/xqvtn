interface ErrorStateProps {
  message: string
  onRetry?: () => void
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="error-state">
      <p className="danger">Error loading data: {message}</p>
      {onRetry ? (
        <button className="button button-accent" onClick={onRetry}>
          Retry
        </button>
      ) : null}
    </div>
  )
}
