type SubscriptionLoadErrorProps = {
  message: string
  onRetry: () => void
}

/**
 * Échec chargement abonnement — message + Réessayer / Accueil (pas redirect auto).
 */
export default function SubscriptionLoadError({ message, onRetry }: SubscriptionLoadErrorProps) {
  return (
    <div className="page" style={{ padding: '2rem', maxWidth: 480 }} data-testid="subscription-load-error">
      <h1>Impossible de vérifier l’accès</h1>
      <p>{message || 'Statut d’abonnement indisponible.'}</p>
      <p style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
        <button type="button" className="btn" onClick={onRetry}>
          Réessayer
        </button>
        <a className="btn secondary" href="/home">
          Accueil
        </a>
      </p>
    </div>
  )
}
