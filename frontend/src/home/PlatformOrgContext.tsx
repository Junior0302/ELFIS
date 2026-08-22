/**
 * Contexte organisation compact — données auth réelles uniquement.
 */

import { Link } from 'react-router-dom'
import { PlatformHomeSection } from './PlatformHomeSection'

export type PlatformOrgContextProps = {
  orgName: string
  orgRole?: string
  memberCount?: number
  connected: boolean
}

export function PlatformOrgContext({
  orgName,
  orgRole,
  memberCount,
  connected,
}: PlatformOrgContextProps) {
  const hasOrg = Boolean(orgName && orgName !== '—')

  return (
    <PlatformHomeSection
      id="home-org"
      title="Organisation"
      description="Contexte plateforme actif."
      level={4}
      className="ph-org"
    >
      <div className="ph-org__card">
        <div className="ph-org__row">
          <span className="ph-org__label">Organisation</span>
          <strong className="ph-org__value">{hasOrg ? orgName : 'Non sélectionnée'}</strong>
        </div>
        {orgRole ? (
          <div className="ph-org__row">
            <span className="ph-org__label">Rôle</span>
            <span className="ph-org__value">{orgRole}</span>
          </div>
        ) : null}
        {typeof memberCount === 'number' && memberCount > 0 ? (
          <div className="ph-org__row">
            <span className="ph-org__label">Accès</span>
            <span className="ph-org__value">
              {memberCount} organisation{memberCount > 1 ? 's' : ''}
            </span>
          </div>
        ) : null}
        <div className="ph-org__row">
          <span className="ph-org__label">Session</span>
          <span className="ph-org__value">{connected ? 'Connecté' : 'Hors ligne'}</span>
        </div>
        <div className="ph-org__links">
          <Link to="/platform/organization">Gérer</Link>
          <Link to="/platform/members">Membres</Link>
          <Link to="/platform/settings">Paramètres</Link>
        </div>
      </div>
    </PlatformHomeSection>
  )
}
