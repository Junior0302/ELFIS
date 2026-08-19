import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../auth'
import { isEnterpriseSetupPath } from '../../enterpriseSetup'
import {
  isPublicProductPath,
  isWelcomePath,
  resolveProductPhase,
} from '../../productPhase'
import { useSubscription } from '../../subscriptionContext'
import ElfisHomeLayout from '../../home/ElfisHomeLayout'
import { isPlatformShellPath } from '../../platform-shell/platformPaths'
import PlatformWorkspaceLayout from '../../platform-workspace/PlatformWorkspaceLayout'
import BootstrapLoadingScreen from '../../platform-routing/BootstrapLoadingScreen'
import OrgInaccessibleScreen from '../../platform-routing/OrgInaccessibleScreen'
import SubscriptionLoadError from '../../platform-routing/SubscriptionLoadError'
import { locationReturnKey, sanitizeReturnPath } from '../../platform-routing/returnPath'
import EnterpriseSetupLayout from './EnterpriseSetupLayout'
import PublicLayout from './PublicLayout'
import SalesWorkspaceLayout from './SalesWorkspaceLayout'
import WorkspaceLayout from './WorkspaceLayout'

function isElfisHomePath(pathname: string): boolean {
  const path = pathname.split('?')[0].split('#')[0] || '/'
  return path === '/home' || path.startsWith('/home/')
}

/**
 * Garde central — PublicLayout / EnterpriseSetup / ElfisHome / Platform / Sales / Compta.
 * Évite tout flash de sidebar métier avant résolution.
 * F1.3.2.3 — pendant loading → BootstrapLoadingScreen (jamais Home).
 */
export default function ProductAccessLayout() {
  const { user, memberships, orgId } = useAuth()
  const { subscription, loading, error, refresh } = useSubscription()
  const location = useLocation()

  const phase = resolveProductPhase(subscription, {
    isPlatformAdmin: Boolean(user?.is_platform_admin),
    // Never treat background refresh as a full product-phase loading gate.
    subscriptionLoading: loading && subscription == null,
  })

  if (phase === 'loading') {
    return <BootstrapLoadingScreen message="Chargement de votre espace…" />
  }

  // Échec API abonnement (pas d’entitlement résolu) → erreur explicite, pas Welcome/Home.
  if (error && subscription == null && !user?.is_platform_admin) {
    return (
      <SubscriptionLoadError
        message={error}
        onRetry={() => {
          void refresh()
        }}
      />
    )
  }

  // Org active hors memberships → choisir org, pas Home silencieux.
  if (
    orgId != null &&
    memberships.length > 0 &&
    !memberships.some((m) => m.organization_id === orgId)
  ) {
    return <OrgInaccessibleScreen />
  }

  if (phase === 'no_entitlement') {
    if (!isPublicProductPath(location.pathname)) {
      return (
        <Navigate
          to="/welcome"
          replace
          state={{ from: locationReturnKey(location) }}
        />
      )
    }
    return <PublicLayout />
  }

  // Entitled sur /welcome : restaurer la route demandée si présente, sinon Home.
  if (isWelcomePath(location.pathname)) {
    const from = (location.state as { from?: string } | null)?.from
    return <Navigate to={sanitizeReturnPath(from, '/home')} replace />
  }

  if (isEnterpriseSetupPath(location.pathname)) {
    return <EnterpriseSetupLayout />
  }

  if (isElfisHomePath(location.pathname)) {
    return <ElfisHomeLayout />
  }

  if (isPlatformShellPath(location.pathname)) {
    return <PlatformWorkspaceLayout />
  }

  if (location.pathname === '/sales' || location.pathname.startsWith('/sales/')) {
    return <SalesWorkspaceLayout />
  }

  return <WorkspaceLayout />
}
