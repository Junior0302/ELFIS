export type PilotCardId =
  | 'salespilot'
  | 'comptapilot'
  | 'docpilot'
  | 'analyticspilot'
  | 'supportpilot'
  | 'hrpilot'

export type PilotCardProps = {
  id: PilotCardId
  name: string
  blurb: string
  className?: string
}

const LABELS: Record<PilotCardId, string> = {
  salespilot: 'Sales',
  comptapilot: 'Compta',
  docpilot: 'Docs',
  analyticspilot: 'Analytics',
  supportpilot: 'Support',
  hrpilot: 'RH',
}

/**
 * Carte Pilot flottante du hero — composant réutilisable.
 * Couleurs via modifiers CSS (pas de style inline).
 */
export function HeroPilotCard({ id, name, blurb, className }: PilotCardProps) {
  return (
    <article
      className={['landing-pilot-card', `landing-pilot-card--${id}`, className]
        .filter(Boolean)
        .join(' ')}
    >
      <span className="landing-pilot-card__mark" aria-hidden="true">
        {LABELS[id].charAt(0)}
      </span>
      <div className="landing-pilot-card__body">
        <h3 className="landing-pilot-card__name">{name}</h3>
        <p className="landing-pilot-card__blurb">{blurb}</p>
      </div>
    </article>
  )
}
