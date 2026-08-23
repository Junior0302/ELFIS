import { SectionCopy } from '../components/SectionCopy'
import { LANDING_MODULAR, LANDING_UPCOMING } from '../landing.copy'
import { PUBLIC_UPCOMING_SPACES } from '../landing.model'

export function HorizonSection() {
  return (
    <section className="landing-block landing-block--plain" aria-labelledby="landing-modular-title">
      <div className="landing-block__inner">
        <p className="landing-kicker">{LANDING_MODULAR.eyebrow}</p>
        <h2 id="landing-modular-title">{LANDING_MODULAR.title}</h2>
        <div className="landing-prose landing-prose--wide">
          <SectionCopy paragraphs={LANDING_MODULAR.paragraphs} />
        </div>
        <p className="landing-axis">{LANDING_MODULAR.close}</p>

        <div id="espaces-avenir" className="landing-upcoming">
          <p className="landing-kicker">{LANDING_UPCOMING.eyebrow}</p>
          <h3>{LANDING_UPCOMING.title}</h3>
          <p className="landing-section__lead">{LANDING_UPCOMING.lead}</p>
          <ul className="landing-upcoming__grid">
            {PUBLIC_UPCOMING_SPACES.map((space) => (
              <li key={space.id}>
                <span className="landing-upcoming__badge">À venir</span>
                <strong>{space.label}</strong>
                <p>{space.description}</p>
              </li>
            ))}
          </ul>
          <p className="landing-upcoming__note">{LANDING_UPCOMING.note}</p>
        </div>
      </div>
    </section>
  )
}
