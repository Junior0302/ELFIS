import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../auth'
import { useSync } from '../../sync/SyncProvider'
import { HealthCenter } from '../../home/HealthCenter'
import { buildHealthLamps, relativeCheckLabel } from '../../home/homeSignals'
import '../../platform-workspace/platform-workspace.css'

const HELP_LINKS = [
  {
    to: '/platform/organization',
    title: 'Organisation',
    description: 'Identité, TVA et coordonnées de l’entreprise.',
  },
  {
    to: '/platform/members',
    title: 'Membres et accès',
    description: 'Équipes, rôles et permissions.',
  },
  {
    to: '/platform/settings',
    title: 'Paramètres',
    description: 'Configuration partagée de la plateforme.',
  },
  {
    to: '/notifications',
    title: 'Notifications',
    description: 'Alertes et activité récente.',
  },
  {
    to: '/platform/communications',
    title: 'Communications',
    description: 'E-mail plateforme et connexions.',
  },
  {
    to: '/platform/banking',
    title: 'Synchronisation bancaire',
    description: 'Connexions, relevés et journal de sync.',
  },
  {
    to: '/platform/relations',
    title: 'Relations',
    description: 'Clients, fournisseurs et identités partagées.',
  },
] as const

/**
 * Aide ELFIS Core — surfaces plateforme uniquement.
 * Ne redirige pas vers Finance / Commercial.
 */
export default function PlatformHelpPage() {
  const { user, token, memberships, orgId } = useAuth()
  const { lastTickAt, mode } = useSync()
  const org = memberships.find((m) => m.organization_id === orgId)
  const connected = Boolean(token && user)
  const orgOk = Boolean(orgId != null && org?.organization_name)
  const syncOk = Boolean(token && orgId != null)

  const lamps = useMemo(
    () =>
      buildHealthLamps({
        connected,
        orgOk,
        syncOk,
        syncMode: mode,
        unreadKnown: syncOk,
      }),
    [connected, orgOk, syncOk, mode],
  )

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h2>Aide et support</h2>
          <p>Centre d’aide ELFIS — organisation, accès et services partagés.</p>
        </div>
      </div>

      <div className="platform-surface-banner">
        <strong>ELFIS Core</strong>
        <p>
          Ces liens restent dans la plateforme. Les assistants métier se trouvent dans leur espace,
          via Espaces.
        </p>
        <div className="platform-surface-banner__actions">
          <Link className="btn secondary" to="/home">
            Accueil ELFIS
          </Link>
          <Link className="btn secondary" to="/platform/settings">
            Paramètres
          </Link>
        </div>
      </div>

      <section className="panel" aria-labelledby="help-topics">
        <h3 id="help-topics">Sujets</h3>
        <ul className="platform-settings__list">
          {HELP_LINKS.map((item) => (
            <li key={item.to}>
              <Link to={item.to} className="platform-settings__link">
                <strong>{item.title}</strong>
                <span className="muted">{item.description}</span>
              </Link>
            </li>
          ))}
        </ul>
      </section>

      <HealthCenter
        lamps={lamps}
        lastCheckLabel={relativeCheckLabel(lastTickAt.notifications)}
        allOk={lamps.every((l) => l.tone === 'green')}
        embedded
      />
    </div>
  )
}
