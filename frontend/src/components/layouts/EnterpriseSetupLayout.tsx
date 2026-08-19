import { useEffect, useState } from 'react'
import { Link, Navigate, Outlet, useLocation } from 'react-router-dom'
import { api } from '../../api'
import { useAuth } from '../../auth'
import {
  ENTERPRISE_SETUP_PATH,
  ENTERPRISE_SETUP_PREPARATION_PATH,
} from '../../enterpriseSetup'
import { EnterpriseSetupProvider } from '../../enterpriseSetupContext'

/**
 * Shell concentré pour l’onboarding entreprise — pas de sidebar métier.
 * Si le setup backend est déjà terminé (hors page préparation), redirige vers le Dashboard.
 */
export default function EnterpriseSetupLayout() {
  const { user, logout, token, orgId } = useAuth()
  const location = useLocation()
  const [setupCompleted, setSetupCompleted] = useState<boolean | null>(null)

  useEffect(() => {
    if (!token || orgId == null) {
      setSetupCompleted(false)
      return
    }
    let cancelled = false
    void api
      .getWorkspaceProvisionStatus(token, orgId)
      .then((status) => {
        if (!cancelled) {
          setSetupCompleted(Boolean(status.setup_completed || status.status === 'completed'))
        }
      })
      .catch(() => {
        if (!cancelled) setSetupCompleted(false)
      })
    return () => {
      cancelled = true
    }
  }, [token, orgId])

  const pathname = location.pathname.replace(/\/+$/, '') || '/'
  const onPreparation = pathname === ENTERPRISE_SETUP_PREPARATION_PATH

  if (setupCompleted === true && !onPreparation) {
    return <Navigate to="/dashboard" replace />
  }

  return (
    <EnterpriseSetupProvider>
      <div className="enterprise-setup-shell">
        <header className="enterprise-setup-shell-header">
          <Link to={ENTERPRISE_SETUP_PATH} className="enterprise-setup-shell-brand" title="ComptaPilot IA">
            <img src="/favicon.svg" alt="" />
            <span>ComptaPilot IA</span>
          </Link>
          <div className="enterprise-setup-shell-actions">
            {user ? (
              <>
                <span className="enterprise-setup-shell-user muted">
                  {user.first_name} {user.last_name}
                </span>
                <Link className="btn secondary" to="/compte">
                  Mon compte
                </Link>
                <button type="button" className="linkish" onClick={logout}>
                  Déconnexion
                </button>
              </>
            ) : null}
          </div>
        </header>
        <main className="enterprise-setup-shell-main">
          <Outlet />
        </main>
      </div>
    </EnterpriseSetupProvider>
  )
}
