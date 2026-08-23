import { SectionCopy } from '../components/SectionCopy'
import { LANDING_IDENTITY, LANDING_PERMISSIONS, LANDING_PLATFORM } from '../landing.copy'

export function PlatformSection() {
  return (
    <section
      id="produit"
      className="landing-block landing-block--soft"
      aria-labelledby="landing-platform-title"
    >
      <div className="landing-block__inner">
        <p className="landing-kicker">{LANDING_PLATFORM.eyebrow}</p>
        <h2 id="landing-platform-title">{LANDING_PLATFORM.title}</h2>
        <p className="landing-section__lead">{LANDING_PLATFORM.lead}</p>
        <p className="landing-section__lead">{LANDING_PLATFORM.body}</p>
        <ul className="landing-principles">
          {LANDING_PLATFORM.principles.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
        <div className="landing-split">
          <article>
            <h3>{LANDING_IDENTITY.title}</h3>
            <div className="landing-prose">
              <SectionCopy paragraphs={LANDING_IDENTITY.paragraphs} />
            </div>
          </article>
          <article>
            <h3>{LANDING_PERMISSIONS.title}</h3>
            <div className="landing-prose">
              <SectionCopy paragraphs={LANDING_PERMISSIONS.paragraphs} />
            </div>
          </article>
        </div>
      </div>
    </section>
  )
}
