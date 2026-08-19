import { NavLink } from 'react-router-dom'
import type { AuthUser } from '../../api'
import {
  canSeePlatformNavItem,
  platformCockpitSections,
  resolvePlatformPermissions,
} from '../../platformCockpitNav'
import {
  ELFIS_FRONTEND_VERSION,
  PLATFORM_ENV_LABEL,
  detectPlatformEnvironment,
} from './platformMeta'

const NAV_ICONS: Record<string, string> = {
  '/elfadmin': '◈',
  '/elfadmin/organisations': '▦',
  '/elfadmin/utilisateurs': '☺',
  '/elfadmin/abonnements': '◎',
  '/elfadmin/documents': '▤',
  '/elfadmin/migration': '⇄',
  '/elfadmin/comptabilite': '∑',
  '/elfadmin/banque': '€',
  '/elfadmin/finance': '◆',
  '/elfadmin/ia': '✦',
  '/elfadmin/notifications': '◉',
  '/elfadmin/rapports': '▥',
  '/elfadmin/system-health': '♥',
  '/elfadmin/logs': '☰',
  '/elfadmin/support': '☎',
  '/elfadmin/configuration': '⚙',
  '/elfadmin/activity': '⏱',
  '/elfadmin/processing': '⚙',
  '/elfadmin/storage': '▣',
  '/elfadmin/incidents': '⚠',
  '/elfadmin/audit': '☑',
  '/elfadmin/securite': '⛨',
  '/elfadmin/observabilite': '◎',
  '/elfadmin/fiabilite': '✓',
}

type Props = {
  user: AuthUser | null
  mobileOpen: boolean
  onCloseMobile: () => void
}

export default function PlatformSidebar({ user, mobileOpen, onCloseMobile }: Props) {
  const effective = resolvePlatformPermissions({
    isPlatformAdmin: Boolean(user?.is_platform_admin),
  })
  const env = detectPlatformEnvironment()
  const roleLabel = user?.is_platform_admin ? 'platform.admin' : 'platform'

  return (
    <>
      {mobileOpen && (
        <button
          type="button"
          className="pc-sidebar-backdrop"
          aria-label="Fermer le menu"
          onClick={onCloseMobile}
        />
      )}
      <aside
        className={`pc-sidebar${mobileOpen ? ' is-open' : ''}`}
        aria-label="Navigation Platform Cockpit"
      >
        <div className="pc-sidebar-brand">
          <span className="pc-sidebar-brand-mark" aria-hidden>
            E
          </span>
          <div>
            <strong>ELFIS Core</strong>
            <span>Platform Cockpit</span>
          </div>
        </div>

        <nav className="pc-sidebar-nav">
          {platformCockpitSections.map((section) => {
            const items = section.items.filter((item) => canSeePlatformNavItem(item, effective))
            if (!items.length) return null
            return (
              <div key={section.title} className="pc-sidebar-section">
                <p className="pc-sidebar-section-title">{section.title}</p>
                {items.map((link) => (
                  <NavLink
                    key={link.to}
                    to={link.to}
                    end={link.end}
                    className={({ isActive }) =>
                      `pc-sidebar-link${isActive ? ' is-active' : ''}`
                    }
                    onClick={onCloseMobile}
                  >
                    <span className="pc-sidebar-icon" aria-hidden>
                      {NAV_ICONS[link.to] || '•'}
                    </span>
                    <span>{link.label}</span>
                  </NavLink>
                ))}
              </div>
            )
          })}
        </nav>

        <div className="pc-sidebar-footer">
          <div className="pc-sidebar-profile">
            <span className="pc-sidebar-avatar" aria-hidden>
              {(user?.email || '?').slice(0, 1).toUpperCase()}
            </span>
            <div>
              <strong title={user?.email || ''}>{user?.email || 'Administrateur'}</strong>
              <span className="pc-sidebar-role">{roleLabel}</span>
            </div>
          </div>
          <div className="pc-sidebar-meta">
            <span className={`pc-env-pill pc-env-${env}`}>{PLATFORM_ENV_LABEL[env]}</span>
            <span className="pc-version">v{ELFIS_FRONTEND_VERSION}</span>
          </div>
          <NavLink to="/dashboard" className="pc-sidebar-back" onClick={onCloseMobile}>
            ← Retour à l’application
          </NavLink>
        </div>
      </aside>
    </>
  )
}
