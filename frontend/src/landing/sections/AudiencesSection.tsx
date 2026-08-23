import { SectionCopy } from '../components/SectionCopy'
import { LANDING_COMPANIES, LANDING_INDEPENDENTS } from '../landing.copy'

export function AudiencesSection() {
  return (
    <section className="landing-block landing-block--plain" aria-labelledby="landing-audiences-title">
      <div className="landing-block__inner">
        <h2 id="landing-audiences-title" className="visually-hidden">
          Indépendants et entreprises
        </h2>
        <div className="landing-split landing-split--equal">
          <article>
            <p className="landing-kicker">{LANDING_INDEPENDENTS.eyebrow}</p>
            <h3>{LANDING_INDEPENDENTS.title}</h3>
            <div className="landing-prose">
              <SectionCopy paragraphs={LANDING_INDEPENDENTS.paragraphs} />
            </div>
          </article>
          <article>
            <p className="landing-kicker">{LANDING_COMPANIES.eyebrow}</p>
            <h3>{LANDING_COMPANIES.title}</h3>
            <div className="landing-prose">
              <SectionCopy paragraphs={LANDING_COMPANIES.paragraphs} />
            </div>
          </article>
        </div>
      </div>
    </section>
  )
}
