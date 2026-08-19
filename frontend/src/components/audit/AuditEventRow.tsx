import type { AuditEvent } from '../../types/audit'
import AuditCategoryBadge from './AuditCategoryBadge'
import AuditSeverityBadge from './AuditSeverityBadge'
import AuditStatusBadge from './AuditStatusBadge'
import { formatLocalTime, narrativeForEvent } from './auditDisplay'

type Props = {
  event: AuditEvent
  onSelect: (event: AuditEvent) => void
  selected?: boolean
}

export default function AuditEventRow({ event, onSelect, selected }: Props) {
  return (
    <button
      type="button"
      className={`audit-event-row${selected ? ' is-selected' : ''}`}
      onClick={() => onSelect(event)}
      aria-pressed={selected}
    >
      <time dateTime={event.occurred_at}>{formatLocalTime(event.occurred_at)}</time>
      <div className="audit-event-main">
        <p className="audit-event-narrative">{narrativeForEvent(event)}</p>
        <div className="audit-event-meta">
          <AuditCategoryBadge category={event.category} />
          <span className="audit-chip">{event.action}</span>
          <AuditSeverityBadge severity={event.severity} />
          <AuditStatusBadge status={event.status} success={event.success} />
          {event.service && <span className="audit-chip">{event.service}</span>}
          {event.organization_id != null && (
            <span className="audit-chip">org #{event.organization_id}</span>
          )}
        </div>
      </div>
    </button>
  )
}
