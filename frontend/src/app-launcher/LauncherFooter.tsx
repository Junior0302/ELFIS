import { Link } from 'react-router-dom'
import { getLauncherFooterLinks } from './launcherModel'

export type LauncherFooterProps = {
  onNavigateAway?: () => void
}

export function LauncherFooter({ onNavigateAway }: LauncherFooterProps) {
  const links = getLauncherFooterLinks()

  return (
    <footer className="launcher-footer">
      <nav className="launcher-footer__nav" aria-label="Raccourcis plateforme">
        {links.map((link) => (
          <Link
            key={link.id}
            className="launcher-footer__link"
            to={link.to}
            onClick={onNavigateAway}
          >
            {link.label}
          </Link>
        ))}
      </nav>
    </footer>
  )
}
