import { Link } from 'react-router-dom'
import { LandingLogo } from '../components/LandingLogo'

const FOOTER_COLS = [
  {
    title: 'Produit',
    links: [
      { href: '#plateforme', label: 'Plateforme' },
      { href: '#solutions', label: 'Solutions' },
      { href: '#tarifs', label: 'Tarifs' },
    ],
  },
  {
    title: 'Pilot',
    links: [
      { href: '#solutions', label: 'ComptaPilot' },
      { href: '#solutions', label: 'SalesPilot' },
      { href: '#solutions', label: 'DocPilot' },
    ],
  },
  {
    title: 'Ressources',
    links: [
      { href: '#ressources', label: 'Fonctionnalités' },
      { href: '#a-propos', label: 'À propos' },
      { href: '/login', label: 'Connexion', router: true },
    ],
  },
] as const

export function Footer() {
  return (
    <footer id="a-propos" className="landing-footer">
      <div className="landing-footer__top">
        <div className="landing-footer__brand">
          <LandingLogo size="sm" />
          <p>Une plateforme. Plusieurs expertises.</p>
        </div>
        <div className="landing-footer__cols">
          {FOOTER_COLS.map((col) => (
            <div key={col.title} className="landing-footer__col">
              <h3>{col.title}</h3>
              <ul>
                {col.links.map((link) => (
                  <li key={link.label}>
                    {'router' in link && link.router ? (
                      <Link to={link.href}>{link.label}</Link>
                    ) : (
                      <a href={link.href}>{link.label}</a>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
      <div className="landing-footer__bottom">
        <p>© {new Date().getFullYear()} ELFIS Core. Tous droits réservés.</p>
        <ul className="landing-footer__legal">
          <li>
            <a href="#a-propos">Mentions légales</a>
          </li>
          <li>
            <a href="#a-propos">Confidentialité</a>
          </li>
        </ul>
        <ul className="landing-footer__social" aria-label="Réseaux sociaux">
          <li>
            <a href="https://www.linkedin.com" rel="noopener noreferrer" target="_blank">
              LinkedIn
            </a>
          </li>
          <li>
            <a href="https://www.youtube.com" rel="noopener noreferrer" target="_blank">
              YouTube
            </a>
          </li>
        </ul>
      </div>
    </footer>
  )
}
