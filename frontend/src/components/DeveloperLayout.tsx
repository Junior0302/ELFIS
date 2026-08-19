import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../auth'
import { developerCockpitSections } from '../developerCockpitNav'
import { developerApi } from '../services/developerApi'

export default function DeveloperLayout() {
  const { user, token, logout } = useAuth()
  const location = useLocation()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [meta, setMeta] = useState<Record<string, unknown> | null>(null)
  const [lastSync, setLastSync] = useState<Date | null>(null)

  const refresh = useCallback(async () => {
    if (!token) return
    try {
      const m = await developerApi.meta(token)
      setMeta(m)
      setLastSync(new Date())
    } catch {
      /* shell non bloquant */
    }
  }, [token])

  useEffect(() => {
    void refresh()
  }, [refresh])

  useEffect(() => {
    setMobileOpen(false)
  }, [location.pathname])

  const env = String(meta?.environment || 'local')
  const backendVersion = String(meta?.backend_version || '—')
  const commit = meta?.git_commit ? String(meta.git_commit) : '—'

  return (
    <div className="dev-cockpit">
      {mobileOpen && (
        <button
          type="button"
          className="dev-sidebar-backdrop"
          aria-label="Fermer le menu"
          onClick={() => setMobileOpen(false)}
        />
      )}
      <aside className={`dev-sidebar${mobileOpen ? ' is-open' : ''}`} aria-label="Developer Cockpit">
        <div className="dev-sidebar-brand">
          <strong>ELFIS Dev</strong>
          <span>Developer Cockpit</span>
        </div>
        <nav className="dev-sidebar-nav">
          {developerCockpitSections.map((section) => (
            <div key={section.title} className="dev-nav-section">
              <p className="dev-nav-section-title">{section.title}</p>
              {section.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) =>
                    `dev-nav-link${isActive ? ' is-active' : ''}${item.available === false ? ' is-muted' : ''}`
                  }
                  onClick={() => setMobileOpen(false)}
                >
                  {item.label}
                  {item.available === false ? <em>RO</em> : null}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
        <div className="dev-sidebar-footer">
          <NavLink to="/elfadmin" className="dev-back-link">
            ← Cockpit Admin
          </NavLink>
          <NavLink to="/dashboard" className="dev-back-link">
            ← Application
          </NavLink>
        </div>
      </aside>

      <div className="dev-workspace">
        <header className="dev-topbar">
          <button
            type="button"
            className="dev-menu-btn"
            aria-label="Ouvrir la navigation"
            onClick={() => setMobileOpen(true)}
          >
            ☰
          </button>
          <div className="dev-topbar-meta">
            <span className="dev-pill">{env}</span>
            <span className="dev-pill">API v{backendVersion}</span>
            <span className="dev-pill">FE 0.8.9</span>
            <span className="dev-pill">git {commit}</span>
            <span className="dev-pill muted">
              sync{' '}
              {lastSync
                ? lastSync.toLocaleTimeString('fr-FR', {
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit',
                  })
                : '—'}
            </span>
          </div>
          <div className="dev-topbar-actions">
            <button type="button" className="dev-btn" onClick={() => void refresh()}>
              Actualiser
            </button>
            <span className="dev-user" title={user?.email || ''}>
              {user?.email}
            </span>
            <button type="button" className="dev-btn ghost" onClick={logout}>
              Déconnexion
            </button>
          </div>
        </header>
        <main className="dev-main">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
