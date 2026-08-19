import { Link } from 'react-router-dom'

type SettingsLink = {
  to: string
  title: string
  description: string
}

const CORE_LINKS: SettingsLink[] = [
  {
    to: '/platform/organization',
    title: 'Organisation',
    description: 'Identité légale, adresse, TVA, logo — partagée entre les Pilots.',
  },
  {
    to: '/compte',
    title: 'Mon compte',
    description: 'Profil personnel et préférences utilisateur.',
  },
  {
    to: '/abonnement',
    title: 'Abonnement',
    description: 'Offre, essai et facturation plateforme.',
  },
  {
    to: '/platform/members',
    title: 'Équipe & accès',
    description: 'Membres, rôles et permissions organisation.',
  },
  {
    to: '/platform/relations',
    title: 'Relations',
    description: 'Clients, fournisseurs et identités partagées (lecture unifiée).',
  },
  {
    to: '/platform/documents',
    title: 'Documents',
    description: 'ELFIS Vault — documents de l’organisation.',
  },
  {
    to: '/platform/communications',
    title: 'Communications',
    description: 'E-mail plateforme, provider et connexions (sans secrets).',
  },
  {
    to: '/platform/aura',
    title: 'Aura',
    description: 'Assistant global ELFIS.',
  },
  {
    to: '/modules',
    title: 'Modules',
    description: 'Découverte et activation des capacités plateforme.',
  },
]

const PRODUCT_LINKS: SettingsLink[] = [
  {
    to: '/settings',
    title: 'Préférences ComptaPilot',
    description: 'Comptes comptables, OCR, seuils — métier finance uniquement.',
  },
  {
    to: '/sales/settings',
    title: 'Paramètres SalesPilot',
    description: 'Configuration CRM et pipelines.',
  },
]

/**
 * Hub officiel des paramètres ELFIS Core (/platform/settings).
 * Pas de faux formulaires — liens vers sections réelles + placeholders documentés.
 */
export default function PlatformSettingsPage() {
  return (
    <div className="page platform-settings">
      <div className="page-head">
        <div>
          <h2>Paramètres ELFIS</h2>
          <p>
            Configuration plateforme partagée. Les réglages métier restent dans chaque Pilot.
          </p>
        </div>
      </div>

      <section className="panel" aria-labelledby="platform-settings-core">
        <h3 id="platform-settings-core">Plateforme</h3>
        <ul className="platform-settings__list">
          {CORE_LINKS.map((item) => (
            <li key={item.to}>
              <Link to={item.to} className="platform-settings__link">
                <strong>{item.title}</strong>
                <span className="muted">{item.description}</span>
              </Link>
            </li>
          ))}
          <li>
            <div className="platform-settings__placeholder" aria-disabled="true">
              <strong>Sécurité</strong>
              <span className="muted">Bientôt — politiques d’accès et sessions.</span>
            </div>
          </li>
        </ul>
      </section>

      <section className="panel" aria-labelledby="platform-settings-products">
        <h3 id="platform-settings-products">Réglages produit</h3>
        <ul className="platform-settings__list">
          {PRODUCT_LINKS.map((item) => (
            <li key={item.to}>
              <Link to={item.to} className="platform-settings__link">
                <strong>{item.title}</strong>
                <span className="muted">{item.description}</span>
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
