import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { LoginBrandPanel } from './LoginBrandPanel'
import { LoginIllustration } from './LoginIllustration'
import { LoginSpaceDock } from './LoginSpaceDock'
import './login.css'

type ElfisAuthShellProps = {
  children: ReactNode
}

/**
 * Chrome public ELFIS Core — login, inscription, mot de passe oublié.
 * Ne contient aucun flux auth.
 */
export function ElfisAuthShell({ children }: ElfisAuthShellProps) {
  return (
    <div className="elfis-login" data-product="elfis-core">
      <div className="elfis-login__atmosphere" aria-hidden>
        <LoginIllustration />
      </div>

      <header className="elfis-login__top">
        <Link to="/" className="elfis-login__brand" aria-label="ELFIS Core — accueil">
          <img src="/favicon.svg" alt="" width={40} height={40} decoding="async" />
          <span>
            <strong>ELFIS Core</strong>
            <small>Plateforme</small>
          </span>
        </Link>
        <Link className="elfis-login__back" to="/">
          Retour au site
        </Link>
      </header>

      <div className="elfis-login__grid">
        <LoginBrandPanel />
        <section className="elfis-login__panel">{children}</section>
      </div>

      <footer className="elfis-login__footer">
        <p>© 2026 ELFIS Core. Tous droits réservés.</p>
        <LoginSpaceDock />
      </footer>
    </div>
  )
}
