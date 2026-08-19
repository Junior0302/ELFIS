import type { AuditEvent } from '../../types/audit'
import AuditEventRow from './AuditEventRow'

type Props = {
  events: AuditEvent[]
  selectedId?: string | null
  onSelect: (event: AuditEvent) => void
}

export default function AuditTimeline({ events, selectedId, onSelect }: Props) {
  return (
    <div className="audit-timeline" role="list" aria-label="Timeline des événements">
      {events.map((event) => (
        <div key={event.id} role="listitem">
          <AuditEventRow
            event={event}
            selected={selectedId === event.id}
            onSelect={onSelect}
          />
        </div>
      ))}
    </div>
  )
}
