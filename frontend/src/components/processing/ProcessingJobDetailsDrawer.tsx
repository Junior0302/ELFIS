import type { ProcessingAttempt, ProcessingJob, ProcessingStep } from '../../services/documentProcessingApi'
import ProcessingAttemptsList from './ProcessingAttemptsList'
import ProcessingJobStatusBadge from './ProcessingJobStatusBadge'
import ProcessingStepsTimeline from './ProcessingStepsTimeline'

export default function ProcessingJobDetailsDrawer({
  job,
  steps,
  attempts,
  canCancel,
  canRetry,
  onClose,
  onCancel,
  onRetry,
}: {
  job: ProcessingJob | null
  steps: ProcessingStep[]
  attempts: ProcessingAttempt[]
  canCancel: boolean
  canRetry: boolean
  onClose: () => void
  onCancel: () => void
  onRetry: () => void
}) {
  if (!job) return null
  return (
    <aside className="processing-drawer" aria-label="Détail job">
      <header>
        <h2>Job {job.id.slice(0, 8)}…</h2>
        <button type="button" onClick={onClose}>
          Fermer
        </button>
      </header>
      <p>
        <ProcessingJobStatusBadge status={job.status} /> · {job.progress_percent}% · {job.pipeline_key}
      </p>
      <p className="muted">
        document {job.document_id.slice(0, 8)}… · version {job.document_version_id.slice(0, 8)}…
      </p>
      {job.last_error_code ? (
        <p role="status">
          Erreur : {job.last_error_code}
          {job.last_error_message_sanitized ? ` — ${job.last_error_message_sanitized}` : ''}
        </p>
      ) : null}
      <div className="processing-drawer__actions">
        {canCancel ? (
          <button type="button" onClick={onCancel}>
            Annuler
          </button>
        ) : null}
        {canRetry ? (
          <button type="button" onClick={onRetry}>
            Relancer
          </button>
        ) : null}
      </div>
      <h3>Étapes</h3>
      <ProcessingStepsTimeline steps={steps} />
      <h3>Tentatives</h3>
      <ProcessingAttemptsList attempts={attempts} />
    </aside>
  )
}
