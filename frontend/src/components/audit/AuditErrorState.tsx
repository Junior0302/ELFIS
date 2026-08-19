export default function AuditErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="platform-alert" role="alert">
      <p>{message || "Impossible de charger l'Activity Center."}</p>
      {onRetry && (
        <button type="button" className="platform-btn" onClick={onRetry}>
          Réessayer
        </button>
      )}
    </div>
  )
}
