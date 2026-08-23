import { SectionCopy } from '../components/SectionCopy'
import { LANDING_SECURITY, LANDING_TRACEABILITY } from '../landing.copy'

export function SecuritySection() {
  return (
    <section
      id="securite"
      className="landing-block landing-block--dark"
      aria-labelledby="landing-security-title"
    >
      <div className="landing-block__aura" aria-hidden />
      <div className="landing-block__inner">
        <p className="landing-kicker landing-kicker--light">{LANDING_SECURITY.eyebrow}</p>
        <h2 id="landing-security-title">{LANDING_SECURITY.title}</h2>
        <div className="landing-prose landing-prose--light">
          <SectionCopy paragraphs={LANDING_SECURITY.paragraphs} />
        </div>
        <ul className="landing-pillars">
          {LANDING_SECURITY.pillars.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
        <article className="landing-trace">
          <h3>{LANDING_TRACEABILITY.title}</h3>
          <div className="landing-prose landing-prose--light">
            <SectionCopy paragraphs={LANDING_TRACEABILITY.paragraphs} />
          </div>
        </article>
      </div>
    </section>
  )
}
