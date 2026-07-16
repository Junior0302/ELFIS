import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../auth'

const platformLinks = [
  { to: '/platform', label: 'Synthèse', end: true },
  { to: '/platform/organisations', label: 'Organisations' },
  { to: '/platform/utilisateurs', label: 'Utilisateurs' },
  { to: '/platform/abonnements', label: 'Abonnements' },
]

export default function PlatformLayout() {
  const { user, logout } = useAuth()

  return (
    <div className="platform-shell">
      <header className="platform-header">
        <div>
          <span className="platform-kicker">ELFIS Core</span>
          <strong>Administration plateforme</strong>
        </div>
        <div className="platform-account">
          <span>{user?.email}</span>
          <NavLink to="/dashboard">Retour au produit</NavLink>
          <button type="button" onClick={logout}>Déconnexion</button>
        </div>
      </header>
      <nav className="platform-nav" aria-label="Administration plateforme">
        {platformLinks.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.end}
            className={({ isActive }) => (isActive ? 'active' : undefined)}
          >
            {link.label}
          </NavLink>
        ))}
      </nav>
      <main className="platform-main">
        <Outlet />
      </main>
    </div>
  )
}
