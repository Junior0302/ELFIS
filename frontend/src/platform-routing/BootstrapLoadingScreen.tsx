/**
 * Écran de bootstrap unique — auth / org / subscription.
 * Une transition stable : pas de flash Home ↔ route pendant le loading.
 */

type BootstrapLoadingScreenProps = {
  message?: string
}

export default function BootstrapLoadingScreen({
  message = 'Chargement de votre espace…',
}: BootstrapLoadingScreenProps) {
  return (
    <div
      className="auth-boot bootstrap-loading"
      role="status"
      aria-busy="true"
      aria-live="polite"
      data-testid="bootstrap-loading"
    >
      <div className="loading">{message}</div>
    </div>
  )
}
