import type { HomeHealthLamp } from './homeSignals'
import { PlatformHomeSection } from './PlatformHomeSection'

type HealthCenterProps = {
  lamps: HomeHealthLamp[]
  lastCheckLabel: string
  allOk: boolean
  embedded?: boolean
}

export function HealthCenter({
  lamps,
  lastCheckLabel,
  allOk,
  embedded = false,
}: HealthCenterProps) {
  return (
    <PlatformHomeSection
      id="home-status"
      title="État observé"
      description="Voyants uniquement pour états disponibles."
      level={4}
      className={`cockpit-health ph-health ${embedded ? 'cockpit-health--embedded' : ''}`.trim()}
    >
      <div data-cockpit-health="v1">
        <p className="cockpit-health__summary" role="status">
          {allOk ? 'Plateforme opérationnelle' : 'Certains voyants demandent attention'}
        </p>
        <ul className="cockpit-health__lamps">
          {lamps.map((lamp) => (
            <li key={lamp.id} data-tone={lamp.tone}>
              <span className={`cockpit-health__lamp is-${lamp.tone}`} aria-hidden />
              <span>
                <strong>{lamp.label}</strong>
                <span className="cockpit-health__detail">{lamp.detail}</span>
              </span>
            </li>
          ))}
        </ul>
        <p className="cockpit-health__footer">Dernière vérif : {lastCheckLabel}</p>
      </div>
    </PlatformHomeSection>
  )
}
