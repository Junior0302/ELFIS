import { SectionCopy } from '../components/SectionCopy'
import { LANDING_APPROACH, LANDING_VISION, LANDING_WHY } from '../landing.copy'

export function BrandSection() {
  return (
    <section
      id="pourquoi"
      className="landing-block landing-block--soft"
      aria-labelledby="landing-why-title"
    >
      <div className="landing-block__inner landing-block__inner--narrow">
        <p className="landing-kicker">{LANDING_WHY.eyebrow}</p>
        <h2 id="landing-why-title">{LANDING_WHY.title}</h2>
        <div className="landing-prose">
          <SectionCopy paragraphs={LANDING_WHY.paragraphs} />
        </div>
        <p className="landing-kicker">{LANDING_APPROACH.eyebrow}</p>
        <h3>{LANDING_APPROACH.title}</h3>
        <div className="landing-prose">
          <SectionCopy paragraphs={LANDING_APPROACH.paragraphs} />
        </div>
        <div id="vision" className="landing-vision">
          <p className="landing-kicker">{LANDING_VISION.eyebrow}</p>
          <h3>{LANDING_VISION.title}</h3>
          <div className="landing-prose">
            <SectionCopy paragraphs={LANDING_VISION.paragraphs} />
          </div>
          <p className="landing-axis">{LANDING_VISION.close}</p>
        </div>
      </div>
    </section>
  )
}
