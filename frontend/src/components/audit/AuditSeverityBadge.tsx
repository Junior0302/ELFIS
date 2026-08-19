import type { AuditSeverity } from '../../types/audit'

export default function AuditSeverityBadge({ severity }: { severity: AuditSeverity | string }) {
  const key = String(severity || 'INFO').toLowerCase()
  return (
    <span className={`audit-badge audit-severity-${key}`} title={`Sévérité ${severity}`}>
      {severity}
    </span>
  )
}
