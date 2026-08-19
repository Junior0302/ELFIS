export default function HealthErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="platform-alert">
      <p>{message || 'Impossible de charger System Health.'}</p>
      {onRetry && (
        <button type="button" className="platform-btn" onClick={onRetry}>
          Réessayer
        </button>
      )}
    </div>
  )
}
