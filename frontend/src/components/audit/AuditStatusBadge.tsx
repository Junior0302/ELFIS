import type { AuditStatus } from '../../types/audit'

export default function AuditStatusBadge({ status, success }: { status: AuditStatus | string; success?: boolean }) {
  const key = String(status || (success ? 'SUCCESS' : 'FAILURE')).toLowerCase()
  return (
    <span className={`audit-badge audit-status-${key}`} title={`Statut ${status}`}>
      {status}
    </span>
  )
}
