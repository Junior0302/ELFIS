import type { ProcessingJob } from '../../services/documentProcessingApi'
import ProcessingJobStatusBadge from './ProcessingJobStatusBadge'

export default function ProcessingJobsTable({
  items,
  onSelect,
}: {
  items: ProcessingJob[]
  onSelect: (job: ProcessingJob) => void
}) {
  return (
    <table className="platform-table processing-jobs-table">
      <thead>
        <tr>
          <th>Statut</th>
          <th>Pipeline</th>
          <th>Progression</th>
          <th>Document</th>
          <th>Erreur</th>
          <th>Créé</th>
        </tr>
      </thead>
      <tbody>
        {items.length === 0 ? (
          <tr>
            <td colSpan={6} className="muted">
              Aucun job
            </td>
          </tr>
        ) : null}
        {items.map((job) => (
          <tr key={job.id} onClick={() => onSelect(job)} style={{ cursor: 'pointer' }}>
            <td>
              <ProcessingJobStatusBadge status={job.status} />
            </td>
            <td>{job.pipeline_key}</td>
            <td>{job.progress_percent}%</td>
            <td className="muted">{job.document_id.slice(0, 8)}…</td>
            <td className="muted">{job.last_error_code || '—'}</td>
            <td className="muted">{job.created_at ? new Date(job.created_at).toLocaleString() : '—'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
