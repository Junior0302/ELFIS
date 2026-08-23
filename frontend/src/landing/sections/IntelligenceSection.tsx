import { SectionCopy } from '../components/SectionCopy'
import { LANDING_AUTOMATION, LANDING_DOC_INTELLIGENCE, LANDING_SEARCH } from '../landing.copy'

export function IntelligenceSection() {
  return (
    <section
      id="automatisation"
      className="landing-block landing-block--soft"
      aria-labelledby="landing-ai-title"
    >
      <div className="landing-block__inner">
        <p className="landing-kicker">{LANDING_AUTOMATION.eyebrow}</p>
        <h2 id="landing-ai-title">{LANDING_AUTOMATION.title}</h2>
        <div className="landing-prose landing-prose--wide">
          <SectionCopy paragraphs={LANDING_AUTOMATION.paragraphs} />
        </div>
        <div className="landing-split">
          <article>
            <h3>{LANDING_DOC_INTELLIGENCE.title}</h3>
            <div className="landing-prose">
              <SectionCopy paragraphs={LANDING_DOC_INTELLIGENCE.paragraphs} />
            </div>
          </article>
          <article>
            <h3>{LANDING_SEARCH.title}</h3>
            <div className="landing-prose">
              <SectionCopy paragraphs={LANDING_SEARCH.paragraphs} />
            </div>
          </article>
        </div>
      </div>
    </section>
  )
}
