import { SectionCopy } from '../components/SectionCopy'
import { LANDING_PROBLEM } from '../landing.copy'

export function ProblemSection() {
  return (
    <section
      className="landing-block landing-block--plain landing-problem"
      aria-labelledby="landing-problem-title"
    >
      <div className="landing-block__inner landing-block__inner--narrow">
        <p className="landing-kicker">{LANDING_PROBLEM.eyebrow}</p>
        <h2 id="landing-problem-title">{LANDING_PROBLEM.title}</h2>
        <div className="landing-prose">
          <SectionCopy paragraphs={LANDING_PROBLEM.paragraphs} />
        </div>
      </div>
    </section>
  )
}
