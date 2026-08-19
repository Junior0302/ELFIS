import type { ProcessingAttempt } from '../../services/documentProcessingApi'

export default function ProcessingAttemptsList({ attempts }: { attempts: ProcessingAttempt[] }) {
  return (
    <ul className="processing-attempts-list">
      {attempts.length === 0 ? <li className="muted">Aucune tentative</li> : null}
      {attempts.map((a) => (
        <li key={a.id}>
          #{a.attempt_number} · {a.status}
          {a.duration_ms != null ? ` · ${a.duration_ms} ms` : ''}
          {a.error_code ? ` · ${a.error_code}` : ''}
          {a.error_message_sanitized ? ` — ${a.error_message_sanitized}` : ''}
        </li>
      ))}
    </ul>
  )
}
