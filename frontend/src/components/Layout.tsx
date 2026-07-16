import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../auth'
import SubscriptionBanner from './SubscriptionBanner'

type NavItem = { to: string; label: string; hint: string; permission?: string }

const navSections: { title: string; items: NavItem[] }[] = [
  {
    title: 'Pilotage',
    items: [
      { to: '/dashboard', label: 'Tableau de bord', hint: 'Vue d’ensemble', permission: 'invoice.read' },
      { to: '/copilote', label: 'Copilote IA', hint: 'Questions & conseils', permission: 'ai.analysis' },
    ],
  },
  {
    title: 'Activité',
    items: [
      { to: '/deposit', label: 'Déposer', hint: 'OCR factures', permission: 'invoice.create' },
      { to: '/history', label: 'Comptabilité', hint: 'Documents & exports', permission: 'documents.read' },
      { to: '/facturation', label: 'Facturation', hint: 'Devis & clients', permission: 'invoice.read' },
    ],
  },
  {
    title: 'Administration',
    items: [
      {
        to: '/abonnement',
        label: 'Abonnement',
        hint: 'Essai, carte & factures',
        permission: 'subscription.manage',
      },
      { to: '/organisation', label: 'Organisation', hint: 'Structure & abonnement' },
      {
        to: '/admin/equipe',
        label: 'Admin équipe',
        hint: 'Comptes & droits',
        permission: 'users.manage',
      },
      { to: '/settings', label: 'Paramètres', hint: 'Entreprise & TVA', permission: 'settings.manage' },
      { to: '/compte', label: 'Mon compte', hint: 'Profil & sécurité' },
    ],
  },
]

export default function Layout() {
  const { user, memberships, orgId, setOrgId, logout } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
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

  return (
    <div className="app-shell">
      <header className="mobile-topbar">
        <Link className="mobile-brand" to="/dashboard">
          <img src="/favicon.svg" alt="" />
          <span>ComptaPilot IA</span>
        </Link>
        <button
          type="button"
          className="mobile-menu-toggle"
          aria-label={menuOpen ? 'Fermer le menu' : 'Ouvrir le menu'}
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen((open) => !open)}
        >
          <span />
          <span />
          <span />
        </button>
      </header>
      <button
        type="button"
        className={`mobile-menu-backdrop ${menuOpen ? 'open' : ''}`}
        aria-label="Fermer le menu"
        onClick={() => setMenuOpen(false)}
      />
      <aside className={`sidebar ${menuOpen ? 'open' : ''}`}>
        <div className="brand">
          <Link to="/dashboard" className="brand-mark">
            <img src="/favicon.svg" alt="" />
            <div>
              <h1>ComptaPilot IA</h1>
              <p>Copilote du dirigeant</p>
            </div>
          </Link>
        </div>
        <nav className="nav">
          {navSections.map((section) => {
            const items = section.items.filter((link) => can(link.permission))
            if (items.length === 0) return null
            return (
              <div key={section.title} className="nav-section">
                <p className="nav-section-title">{section.title}</p>
                {items.map((link) => (
                  <NavLink
                    key={link.to}
                    to={link.to}
                    end={link.to === '/dashboard'}
                    className={({ isActive }) => (isActive ? 'active' : undefined)}
                    title={link.hint}
                  >
                    <span className="nav-label">{link.label}</span>
                    <span className="nav-hint">{link.hint}</span>
                  </NavLink>
                ))}
              </div>
            )
          })}
        </nav>
        <div className="sidebar-foot">
          {user && (
            <>
              <strong>
                {user.first_name} {user.last_name}
              </strong>
              {activeMembership && (
                <>
                  <br />
                  <span className="lan-hint">
                    {activeMembership.organization_name} · {activeMembership.role}
                  </span>
                </>
              )}
              <br />
              {user.is_platform_admin && (
                <>
                  <Link to="/elfadmin" className="lan-hint">
                    ELF Admin
                  </Link>
                  <br />
                </>
              )}
              {memberships.length > 1 && (
                <select
                  className="org-select"
                  value={orgId ?? ''}
                  onChange={(e) => setOrgId(Number(e.target.value))}
                  aria-label="Organisation active"
                >
                  {memberships.map((m) => (
                    <option key={m.membership_id} value={m.organization_id}>
                      {m.organization_name} ({m.role})
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
      <main className="main">
        <SubscriptionBanner />
        <Outlet />
      </main>
    </div>
  )
}
