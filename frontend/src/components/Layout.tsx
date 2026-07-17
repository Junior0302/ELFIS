import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../auth'
import { navSections } from '../navConfig'
import { SubscriptionProvider } from '../subscriptionContext'
import { navIcons } from './NavIcons'
import PageGuide from './PageGuide'
import SubscriptionBanner from './SubscriptionBanner'

const SIDEBAR_KEY = 'cp_sidebar_collapsed'

function userInitials(first?: string, last?: string) {
  const a = (first || '').trim().charAt(0)
  const b = (last || '').trim().charAt(0)
  return `${a}${b}`.toUpperCase() || '?'
}

function safeAvatarUrl(url?: string | null) {
  if (!url) return ''
  const trimmed = url.trim()
  if (trimmed.startsWith('https://') || trimmed.startsWith('/')) return trimmed
  return ''
}

function LayoutInner() {
  const { user, memberships, orgId, setOrgId, logout } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem(SIDEBAR_KEY) === '1'
    } catch {
      return false
    }
  })
  const location = useLocation()
  const activeMembership = memberships.find((membership) => membership.organization_id === orgId)
  const can = (permission?: string) =>
    !permission ||
    Boolean(
      activeMembership?.permissions.includes('*') ||
        activeMembership?.permissions.includes(permission),
    )

  useEffect(() => {
    setMenuOpen(false)
  }, [location.pathname])

  useEffect(() => {
    try {
      localStorage.setItem(SIDEBAR_KEY, collapsed ? '1' : '0')
    } catch {
      /* ignore */
    }
  }, [collapsed])

  const avatar = safeAvatarUrl(user?.avatar)
  const initials = userInitials(user?.first_name, user?.last_name)

  return (
    <div className={`app-shell ${collapsed ? 'sidebar-collapsed' : ''}`}>
      <header className="mobile-topbar">
        <Link className="mobile-brand" to="/dashboard">
          <img src="/favicon.svg" alt="" />
          <span>ComptaPilot IA</span>
        </Link>
        <div className="mobile-topbar-actions">
          {user && (
            <Link to="/compte" className="shell-avatar" title="Mon compte" aria-label="Mon compte">
              {avatar ? <img src={avatar} alt="" /> : <span>{initials}</span>}
            </Link>
          )}
          <button
            type="button"
            className={`mobile-menu-toggle ${menuOpen ? 'is-open' : ''}`}
            aria-label={menuOpen ? 'Fermer le menu' : 'Ouvrir le menu'}
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((open) => !open)}
          >
            <span />
            <span />
            <span />
          </button>
        </div>
      </header>
      <button
        type="button"
        className={`mobile-menu-backdrop ${menuOpen ? 'open' : ''}`}
        aria-label="Fermer le menu"
        onClick={() => setMenuOpen(false)}
      />
      <aside className={`sidebar ${menuOpen ? 'open' : ''} ${collapsed ? 'is-collapsed' : ''}`}>
        <div className="brand">
          <Link to="/dashboard" className="brand-mark" title="ComptaPilot IA">
            <img src="/favicon.svg" alt="" />
            <div className="brand-copy">
              <h1>ComptaPilot IA</h1>
              <p>Copilote du dirigeant</p>
            </div>
          </Link>
          <button
            type="button"
            className="sidebar-collapse-btn"
            aria-label={collapsed ? 'Ouvrir le menu' : 'Réduire le menu'}
            title={collapsed ? 'Ouvrir le menu' : 'Réduire le menu'}
            onClick={() => setCollapsed((value) => !value)}
          >
            <span className="sidebar-collapse-chevron" aria-hidden />
          </button>
        </div>
        <nav className="nav">
          {navSections.map((section) => {
            const items = section.items.filter((link) => can(link.permission))
            if (items.length === 0) return null
            return (
              <div key={section.title} className="nav-section">
                <p className="nav-section-title">{section.title}</p>
                {items.map((link) => {
                  const Icon = navIcons[link.to]
                  return (
                    <NavLink
                      key={link.to}
                      to={link.to}
                      end={link.to === '/dashboard'}
                      className={({ isActive }) => (isActive ? 'active' : undefined)}
                      title={collapsed ? `${link.label} — ${link.hint}` : link.guide.join(' ')}
                    >
                      <span className="nav-icon">{Icon ? <Icon /> : null}</span>
                      <span className="nav-text">
                        <span className="nav-label">{link.label}</span>
                        <span className="nav-hint">{link.hint}</span>
                      </span>
                    </NavLink>
                  )
                })}
              </div>
            )
          })}
        </nav>
        <div className="sidebar-foot">
          {user && (
            <>
              <div className="sidebar-foot-user">
                <Link to="/compte" className="shell-avatar compact" title="Mon compte">
                  {avatar ? <img src={avatar} alt="" /> : <span>{initials}</span>}
                </Link>
                <div className="sidebar-foot-meta">
                  <strong>
                    {user.first_name} {user.last_name}
                  </strong>
                  {activeMembership && (
                    <span className="lan-hint">
                      {activeMembership.organization_name} · {activeMembership.role}
                    </span>
                  )}
                </div>
              </div>
              {user.is_platform_admin && (
                <Link to="/elfadmin" className="lan-hint sidebar-admin-link">
                  ELF Admin
                </Link>
              )}
              {memberships.length > 0 && (
                <select
                  className="org-select"
                  value={orgId ?? ''}
                  onChange={(e) => setOrgId(Number(e.target.value))}
                  aria-label="Organisation active"
                >
                  {memberships.map((m) => (
                    <option key={m.membership_id} value={m.organization_id}>
                      {m.organization_name} ({m.role}
                      {m.plan ? ` · ${m.plan}` : ''})
                    </option>
                  ))}
                </select>
              )}
              <button type="button" className="linkish" onClick={logout}>
                Déconnexion
              </button>
            </>
          )}
        </div>
      </aside>
      <div className="shell-main">
        <header className="desktop-topbar">
          <div className="desktop-topbar-left">
            <p className="desktop-topbar-kicker">Espace entreprise</p>
            <strong>{activeMembership?.organization_name || 'ComptaPilot IA'}</strong>
          </div>
          <div className="desktop-topbar-right">
            {memberships.length > 1 && (
              <select
                className="org-select topbar-org"
                value={orgId ?? ''}
                onChange={(e) => setOrgId(Number(e.target.value))}
                aria-label="Organisation active"
              >
                {memberships.map((m) => (
                  <option key={m.membership_id} value={m.organization_id}>
                    {m.organization_name}
                  </option>
                ))}
              </select>
            )}
            {user && (
              <Link to="/compte" className="shell-user-chip" title="Mon compte">
                <span className="shell-user-chip-text">
                  <strong>
                    {user.first_name} {user.last_name}
                  </strong>
                  <span>{user.email}</span>
                </span>
                <span className="shell-avatar">
                  {avatar ? <img src={avatar} alt="" /> : <span>{initials}</span>}
                </span>
              </Link>
            )}
          </div>
        </header>
        <main className="main">
          <SubscriptionBanner />
          <PageGuide />
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export default function Layout() {
  return (
    <SubscriptionProvider>
      <LayoutInner />
    </SubscriptionProvider>
  )
}
