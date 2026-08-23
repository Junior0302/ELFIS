import { SectionCopy } from '../components/SectionCopy'
import { LANDING_DATA, LANDING_WORKFLOW } from '../landing.copy'

export function ContinuitySection() {
  return (
    <section
      id="solutions"
      className="landing-block landing-block--soft"
      aria-labelledby="landing-workflow-title"
    >
      <div className="landing-block__inner">
        <p className="landing-kicker">{LANDING_WORKFLOW.eyebrow}</p>
        <h2 id="landing-workflow-title">{LANDING_WORKFLOW.title}</h2>
        <div className="landing-prose landing-prose--wide">
          <SectionCopy paragraphs={LANDING_WORKFLOW.paragraphs} />
        </div>
        <ol className="landing-flow">
          {LANDING_WORKFLOW.steps.map((step, index) => (
            <li key={step.label}>
              <span className="landing-flow__index" aria-hidden>
                {String(index + 1).padStart(2, '0')}
              </span>
              <strong>{step.label}</strong>
              <span>{step.space}</span>
            </li>
          ))}
        </ol>
        <p className="landing-axis">{LANDING_WORKFLOW.axis}</p>
        <p className="landing-section__lead">{LANDING_WORKFLOW.close}</p>

        <div className="landing-data">
          <h3>{LANDING_DATA.title}</h3>
          <div className="landing-prose landing-prose--wide">
            <SectionCopy paragraphs={LANDING_DATA.paragraphs} />
          </div>
          <ul className="landing-lineage" aria-label="Continuité d’une information">
            {LANDING_DATA.lineage.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          <ul className="landing-outcomes">
            {LANDING_DATA.outcomes.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  )
}
