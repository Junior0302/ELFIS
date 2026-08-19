export type TimelineStep = {
  id: string
  label: string
  description: string
}

type WorkflowTimelineProps = {
  steps: TimelineStep[]
}

/** Timeline verticale / horizontale responsive du parcours métier. */
export function WorkflowTimeline({ steps }: WorkflowTimelineProps) {
  return (
    <ol className="landing-timeline" aria-label="Parcours commercial à financier">
      {steps.map((step, index) => (
        <li key={step.id} className="landing-timeline__item">
          <div className="landing-timeline__node" aria-hidden="true">
            <span className="landing-timeline__index">{index + 1}</span>
          </div>
          <div className="landing-timeline__content">
            <h3 className="landing-timeline__label">{step.label}</h3>
            <p className="landing-timeline__desc">{step.description}</p>
          </div>
          {index < steps.length - 1 ? (
            <span className="landing-timeline__connector" aria-hidden="true" />
          ) : null}
        </li>
      ))}
    </ol>
  )
}
