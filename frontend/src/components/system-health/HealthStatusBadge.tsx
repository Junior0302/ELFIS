import type { HealthStatus } from '../../types/systemHealth'

const LABEL: Record<HealthStatus, string> = {
  healthy: 'Healthy',
  degraded: 'Degraded',
  unhealthy: 'Critical',
  unknown: 'Unknown',
  disabled: 'Disabled',
}

export default function HealthStatusBadge({ status }: { status: HealthStatus }) {
  return (
    <span className={`platform-pill health-status-badge health-status-${status}`}>
      {LABEL[status] || status}
    </span>
  )
}
