import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'

const links: { to: string; label: string; hint: string; permission?: string }[] = [
  { to: '/', label: 'Tableau de bord', hint: 'Vue d’ensemble', permission: 'invoice.read' },
  { to: '/copilote', label: 'Copilote IA', hint: 'Discutez finance', permission: 'ai.analysis' },
  { to: '/deposit', label: 'Déposer', hint: 'PDF ou photo OCR', permission: 'invoice.create' },
  { to: '/history', label: 'Comptabilité', hint: 'Factures & exports', permission: 'documents.read' },
  { to: '/facturation', label: 'Facturation', hint: 'Devis & clients', permission: 'invoice.read' },
  { to: '/banque', label: 'Banque', hint: 'Solde & mouvements', permission: 'bank.read' },
  { to: '/tresorerie', label: 'Trésorerie', hint: 'Prévisions 30/60/90 j', permission: 'finance.read' },
  { to: '/organisation', label: 'Organisation', hint: 'Entreprise & équipes' },
  { to: '/compte', label: 'Mon compte', hint: 'Profil & sécurité' },
  { to: '/modules', label: 'Modules', hint: 'Toute la plateforme' },
  { to: '/settings', label: 'Paramètres', hint: 'Entreprise & TVA' },
]

export default function Layout() {
  const { user, memberships, orgId, setOrgId, logout } = useAuth()
  const [aiMode, setAiMode] = useState<string>('…')
  const [lanHint, setLanHint] = useState('')
  const activeMembership = memberships.find((membership) => membership.organization_id === orgId)
  const can = (permission?: string) =>
    !permission ||
    Boolean(
      activeMembership?.permissions.includes('*') ||
        activeMembership?.permissions.includes(permission),
    )

  useEffect(() => {
    api
      .health()
      .then((h) => setAiMode(h.ai_mode === 'openai' ? 'IA conversationnelle' : 'Réponses guidées'))
      .catch(() => setAiMode('API hors ligne'))

    const host = window.location.hostname
    if (host && host !== 'localhost' && host !== '127.0.0.1') {
      setLanHint(`${window.location.host}`)
    } else {
      setLanHint('')
    }
  }, [])

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <img src="/favicon.svg" alt="" />
            <div>
              <h1>ComptaPilot IA</h1>
              <p>Copilote du dirigeant</p>
            </div>
          </div>
        </div>
        <nav className="nav">
          {links.filter((link) => can(link.permission)).map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.to === '/'}
              className={({ isActive }) => (isActive ? 'active' : undefined)}
              title={link.hint}
            >
              <span className="nav-label">{link.label}</span>
              <span className="nav-hint">{link.hint}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-foot">
          {user ? (
            <>
              <strong>
                {user.first_name} {user.last_name}
              </strong>
              <br />
              <Link to="/compte" className="lan-hint">
                Gérer mon profil
              </Link>
              <br />
              {memberships.length > 0 && (
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
          ) : (
            <>
              <strong>{aiMode}</strong>
              <br />
              <Link to="/login" className="lan-hint">
                Se connecter
              </Link>
            </>
          )}
          {lanHint && (
            <>
              <br />
              <span className="lan-hint">Réseau : {lanHint}</span>
            </>
          )}
        </div>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  )
}
