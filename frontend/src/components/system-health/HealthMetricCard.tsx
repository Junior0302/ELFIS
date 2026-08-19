import type { HealthMetric } from '../../types/systemHealth'

export default function HealthMetricCard({ metric }: { metric: HealthMetric }) {
  return (
    <article className="health-metric-card">
      <span>{metric.label}</span>
      <strong>
        {metric.value ?? '—'}
        {metric.unit ? ` ${metric.unit}` : ''}
      </strong>
      {metric.description && <p>{metric.description}</p>}
    </article>
  )
}
