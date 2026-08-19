import type { HomeHealthLamp } from './homeSignals'

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
    <section
      className={`cockpit-health ${embedded ? 'cockpit-health--embedded' : ''}`.trim()}
      id="home-status"
      aria-labelledby="home-health-title"
      data-cockpit-health="v1"
    >
      <p className="cockpit-health__eyebrow" id="home-health-title">
        Health Center
      </p>
      <p className="cockpit-health__summary" role="status">
        {allOk ? 'Systèmes observés en bon état' : 'Certains voyants demandent attention'}
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
      <p className="cockpit-health__footer">
        Voyants uniquement pour états disponibles · Dernière vérif : {lastCheckLabel}
      </p>
    </section>
  )
}
