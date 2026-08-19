import type { ProcessingStep } from '../../services/documentProcessingApi'
import ProcessingJobStatusBadge from './ProcessingJobStatusBadge'

export default function ProcessingStepsTimeline({ steps }: { steps: ProcessingStep[] }) {
  const ordered = [...steps].sort((a, b) => a.sequence_number - b.sequence_number)
  return (
    <ol className="processing-steps-timeline">
      {ordered.map((s) => (
        <li key={s.id}>
          <span className="muted">#{s.sequence_number}</span> {s.step_key}{' '}
          <ProcessingJobStatusBadge status={s.status} />
          {s.last_error_code ? <span className="muted"> · {s.last_error_code}</span> : null}
        </li>
      ))}
    </ol>
  )
}
