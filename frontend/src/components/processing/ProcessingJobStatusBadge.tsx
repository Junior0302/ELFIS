import type { ProcessingJobStatus } from '../../services/documentProcessingApi'

const LABELS: Record<string, string> = {
  pending: 'En attente',
  queued: 'File',
  running: 'En cours',
  retrying: 'Retry',
  completed: 'Terminé',
  partially_completed: 'Partiel',
  failed: 'Échec',
  cancelled: 'Annulé',
  timed_out: 'Timeout',
  blocked: 'Bloqué',
}

export default function ProcessingJobStatusBadge({ status }: { status: ProcessingJobStatus | string }) {
  return (
    <span className={`processing-status processing-status--${status}`} title={status}>
      {LABELS[status] || status}
    </span>
  )
}
