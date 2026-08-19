import { Link } from 'react-router-dom'
import {
  actionPathOf,
  actionTypeOf,
  decisionSeverityLabel,
  executionStatusLabel,
} from '../decisionCenter'
import type { WorkQueueItem } from '../workQueue'
import { UiBadge } from '../ui/UiStates'

type Props = {
  item: WorkQueueItem
  busy?: boolean
  onStart?: (id: string) => void
  onDismiss?: (id: string) => void
}

export default function WorkQueueItemCard({ item, busy, onStart, onDismiss }: Props) {
  const start = item.available_actions.find((a) => actionTypeOf(a) === 'start' && a.enabled)
  const resume = item.available_actions.find((a) => actionTypeOf(a) === 'resume' && a.enabled)
  const dismiss = item.available_actions.find((a) => actionTypeOf(a) === 'dismiss' && a.enabled)
  const source = item.available_actions.find((a) => actionTypeOf(a) === 'open_source' && a.enabled)
  const detailPath = `/decisions/${item.decision_id}`

  return (
    <article className={`panel work-queue-item severity-${item.severity}`} aria-labelledby={`wq-${item.decision_id}`}>
      <div className="decision-card-head">
        <UiBadge tone={item.severity === 'high' || item.severity === 'critical' ? 'warn' : 'neutral'}>
          {decisionSeverityLabel(item.severity)}
        </UiBadge>
        {item.is_blocking ? <UiBadge tone="warn">Bloquant</UiBadge> : null}
        {item.progress_label ? <UiBadge tone="neutral">{item.progress_label}</UiBadge> : null}
        <h3 id={`wq-${item.decision_id}`}>
          <Link to={detailPath}>{item.title}</Link>
        </h3>
      </div>
      <p>{item.summary}</p>
      {item.waiting_reason ? (
        <p className="muted" role="status">
          <strong>{item.waiting_reason.label}</strong>
          {item.waiting_reason.description ? ` — ${item.waiting_reason.description}` : ''}
        </p>
      ) : null}
      <p className="muted">
        {executionStatusLabel(item.execution_status)}
        {item.age_label ? ` · ${item.age_label}` : ''}
        {item.last_activity ? ` · ${item.last_activity}` : ''}
      </p>
      <div className="actions decision-card-actions">
        {start && onStart ? (
          <button type="button" className="btn" disabled={busy} aria-busy={busy} onClick={() => onStart(item.decision_id)}>
            {busy ? '…' : start.label}
          </button>
        ) : null}
        {resume ? (
          <Link className="btn" to={actionPathOf(resume) || detailPath}>
            {resume.label}
          </Link>
        ) : (
          <Link className="btn secondary" to={detailPath}>
            Ouvrir
          </Link>
        )}
        {source && actionPathOf(source) ? (
          <Link className="btn secondary" to={actionPathOf(source)!}>
            {source.label}
          </Link>
        ) : null}
        {dismiss && onDismiss ? (
          <button type="button" className="btn secondary" disabled={busy} onClick={() => onDismiss(item.decision_id)}>
            {dismiss.label}
          </button>
        ) : null}
      </div>
    </article>
  )
}
