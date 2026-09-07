import { Link, Outlet } from 'react-router-dom'
import { useAuth } from '../../auth'

/**
 * Shell « pré-workspace » — Welcome, Abonnement, Compte (sans sidebar métier).
 * Identité ELFIS Core (même lockup que login / landing).
 * Les providers sont fournis par le parent (AppShellProviders / Layout).
 */
export default function PublicLayout() {
  const { user, logout } = useAuth()

  return (
    <div className="public-shell" data-product="elfis-core">
      <header className="public-shell-header">
        <Link to="/welcome" className="public-shell-brand" aria-label="ELFIS Core — accueil">
          <img src="/elfis-core-mark.svg" alt="" width={32} height={32} decoding="async" />
          <span>
            <strong>ELFIS Core</strong>
            <small>Plateforme</small>
          </span>
        </Link>
        <div className="public-shell-actions">
          {user ? (
            <>
              <span className="public-shell-user muted">
                {user.first_name} {user.last_name}
              </span>
              <Link className="btn secondary public-shell-link" to="/compte">
                Mon compte
              </Link>
              <button type="button" className="linkish" onClick={logout}>
                Déconnexion
              </button>
            </>
          ) : (
            <Link className="btn secondary" to="/login">
              Connexion
            </Link>
          )}
        </div>
      </header>
      <main className="public-shell-main">
        <Outlet />
      </main>
    </div>
  )
}
