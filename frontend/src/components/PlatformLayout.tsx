import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../auth'

const elfAdminLinks = [
  { to: '/elfadmin', label: 'Synthèse', end: true },
  { to: '/elfadmin/utilisateurs', label: 'Utilisateurs' },
  { to: '/elfadmin/organisations', label: 'Organisations' },
  { to: '/elfadmin/abonnements', label: 'Abonnements' },
  { to: '/elfadmin/emails-pro', label: 'Emails pro' },
]

export default function PlatformLayout() {
  const { user, logout } = useAuth()

  return (
    <div className="platform-shell">
      <header className="platform-header">
        <div>
          <span className="platform-kicker">ELFIS Core</span>
          <strong>ELF Admin</strong>
        </div>
        <div className="platform-account">
          <span>{user?.email}</span>
          <NavLink to="/dashboard">Retour au produit</NavLink>
          <button type="button" onClick={logout}>
            Déconnexion
          </button>
        </div>
      </header>
      <nav className="platform-nav" aria-label="ELF Admin">
        {elfAdminLinks.map((link) => (
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
