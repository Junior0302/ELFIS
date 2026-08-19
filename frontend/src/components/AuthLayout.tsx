import { Link, Outlet } from 'react-router-dom'
import './auth.css'

const bullets = [
  {
    title: 'Une identité unique',
    text: 'Un compte pour toute la plateforme ELFIS Core.',
  },
  {
    title: 'Vos applications réunies',
    text: 'ComptaPilot, SalesPilot et les prochains Pilot.',
  },
  {
    title: 'Vos données protégées',
    text: 'Organisation, droits et continuité sécurisées.',
  },
]

/**
 * Layout auth pour register / forgot-password (identité ELFIS Core).
 * Login a son propre module `src/login/`.
 */
export default function AuthLayout() {
  return (
    <div className="auth-shell auth-shell--elfis" data-product="elfis-core">
      <aside className="auth-aside">
        <div className="auth-aside-glow" aria-hidden="true" />
        <div className="auth-aside-inner">
          <Link to="/" className="auth-brand">
            <img src="/favicon.svg" alt="" className="auth-logo" width={48} height={48} />
            <span>
              <strong>ELFIS Core</strong>
              <small>Plateforme professionnelle</small>
            </span>
          </Link>
          <p className="auth-kicker">Espace sécurisé</p>
          <h1 className="auth-title">Une connexion. Tout votre écosystème.</h1>
          <p className="auth-lead">
            Accédez à ComptaPilot, SalesPilot et aux prochaines applications ELFIS depuis un espace
            unique et sécurisé.
          </p>
          <ul className="auth-bullets">
            {bullets.map((item) => (
              <li key={item.title}>
                <span className="auth-bullet-icon" aria-hidden="true" />
                <div>
                  <strong>{item.title}</strong>
                  <small>{item.text}</small>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </aside>
      <main className="auth-main">
        <Outlet />
      </main>
    </div>
  )
}
