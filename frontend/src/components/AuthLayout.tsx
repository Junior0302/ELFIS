import { Outlet } from 'react-router-dom'
import './auth.css'

export default function AuthLayout() {
  return (
    <div className="auth-shell">
      <aside className="auth-aside">
        <div className="auth-aside-inner">
          <img src="/favicon.svg" alt="" className="auth-logo" width={48} height={48} />
          <p className="auth-kicker">ELFIS Core · KATUKU</p>
          <h1 className="auth-title">ComptaPilot IA</h1>
          <p className="auth-lead">
            Le copilote financier des dirigeants — comptabilité, trésorerie, facturation et décisions
            assistées par l&apos;IA.
          </p>
          <ul className="auth-bullets">
            <li>Authentification Firebase (email / mot de passe)</li>
            <li>Vos données réelles — sans comptes fictifs</li>
            <li>Copilote financier pour diriger</li>
          </ul>
        </div>
      </aside>
      <main className="auth-main">
        <Outlet />
      </main>
    </div>
  )
}
