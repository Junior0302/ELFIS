import { Link } from 'react-router-dom'
import type { AuthUser } from '../../api'
import {
  PLATFORM_ENV_LABEL,
  type GlobalHealthTone,
  type PlatformEnvKind,
} from './platformMeta'

type Props = {
  pageTitle: string
  env: PlatformEnvKind
  healthTone: GlobalHealthTone
  healthLabel: string
  lastSync: Date | null
  criticalCount: number
  user: AuthUser | null
  refreshing?: boolean
  onRefresh: () => void
  onOpenNav: () => void
}

export default function PlatformTopbar({
  pageTitle,
  env,
  healthTone,
  healthLabel,
  lastSync,
  criticalCount,
  user,
  refreshing,
  onRefresh,
  onOpenNav,
}: Props) {
  return (
    <header className="pc-topbar">
      <div className="pc-topbar-left">
        <button
          type="button"
          className="pc-topbar-menu"
          aria-label="Ouvrir la navigation"
          onClick={onOpenNav}
        >
          ☰
        </button>
        <nav className="pc-breadcrumb" aria-label="Fil d’Ariane">
          <Link to="/elfadmin">ELFIS Core</Link>
          <span aria-hidden>/</span>
          <Link to="/elfadmin">Platform Cockpit</Link>
          <span aria-hidden>/</span>
          <span aria-current="page">{pageTitle}</span>
        </nav>
        <h1 className="pc-topbar-title">{pageTitle}</h1>
      </div>

      <div className="pc-topbar-right">
        <span className={`pc-env-pill pc-env-${env}`} title="Environnement">
          {PLATFORM_ENV_LABEL[env]}
        </span>
        <span
          className={`pc-health-pill pc-health-${healthTone}`}
          title="Statut global plateforme"
        >
          <span className="pc-health-dot" aria-hidden />
          {healthLabel}
        </span>
        {criticalCount > 0 && (
          <span className="pc-critical-chip" title="Incidents / services critiques">
            {criticalCount} critique{criticalCount > 1 ? 's' : ''}
          </span>
        )}
        <span className="pc-topbar-sync muted">
          Sync{' '}
          {lastSync
            ? lastSync.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
            : '—'}
        </span>
        <button
          type="button"
          className="pc-btn pc-btn-ghost"
          onClick={onRefresh}
          disabled={refreshing}
          aria-label="Actualiser les données cockpit"
        >
          {refreshing ? '…' : 'Actualiser'}
        </button>
        <div className="pc-topbar-user" title={user?.email || ''}>
          <span className="pc-sidebar-avatar" aria-hidden>
            {(user?.email || '?').slice(0, 1).toUpperCase()}
          </span>
          <span className="pc-topbar-user-email">{user?.email}</span>
        </div>
      </div>
    </header>
  )
}
