import { Link } from 'react-router-dom'
import { LandingLogo } from '../components/LandingLogo'
import { LANDING_FOOTER, LANDING_NAV } from '../landing.copy'

type FooterProps = {
  isAuthenticated: boolean
}

function FooterLink({ href, label }: { href: string; label: string }) {
  if (href.startsWith('/')) {
    return <Link to={href}>{label}</Link>
  }
  return <a href={href}>{label}</a>
}

function columnLinks(
  title: string,
  links: readonly { href: string; label: string }[],
  isAuthenticated: boolean,
) {
  const visible = isAuthenticated
    ? links.filter((link) => link.href !== '/register' && link.href !== '/login')
    : [...links]

  if (isAuthenticated && title === 'Entreprise') {
    visible.push({ href: LANDING_NAV.homeTo, label: LANDING_NAV.openWorkspace })
  }

  return visible
}

export function Footer({ isAuthenticated }: FooterProps) {
  return (
    <footer className="landing-footer">
      <div className="landing-footer__top">
        <div className="landing-footer__brand">
          <LandingLogo size="sm" />
          <p>{LANDING_FOOTER.tagline}</p>
        </div>
        <div className="landing-footer__cols">
          {LANDING_FOOTER.columns.map((col) => (
            <div key={col.title} className="landing-footer__col">
              <h3>{col.title}</h3>
              <ul>
                {columnLinks(col.title, col.links, isAuthenticated).map((link) => (
                  <li key={link.label}>
                    <FooterLink href={link.href} label={link.label} />
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
      <div className="landing-footer__bottom">
        <p>© {new Date().getFullYear()} ELFIS Core. Tous droits réservés.</p>
      </div>
    </footer>
  )
}
