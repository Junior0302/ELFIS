import type { HealthCheckResult } from '../../types/systemHealth'
import HealthStatusBadge from './HealthStatusBadge'

export default function HealthServiceCard({ service }: { service: HealthCheckResult }) {
  const topMetrics = service.metrics.slice(0, 3)
  const tone = service.status === 'unhealthy' ? 'critical' : service.status
  return (
    <article
      className={`pc-health-card health-service-card health-card-${service.status} pc-health-${tone}`}
    >
      <header className="health-service-card-header">
        <div>
          <strong>{service.service_name}</strong>
          <span className="health-service-category">{service.category}</span>
        </div>
        <HealthStatusBadge status={service.status} />
      </header>
      <p className="health-service-summary">{service.summary || 'Donnée indisponible'}</p>
      <dl className="health-service-meta">
        <div>
          <dt>Latence</dt>
          <dd>{service.latency_ms != null ? `${service.latency_ms} ms` : 'Donnée indisponible'}</dd>
        </div>
        <div>
          <dt>Version</dt>
          <dd>{service.version || 'Donnée indisponible'}</dd>
        </div>
        <div>
          <dt>Contrôle</dt>
          <dd>
            {service.checked_at
              ? new Date(service.checked_at).toLocaleString('fr-FR')
              : 'Donnée indisponible'}
          </dd>
        </div>
      </dl>
      {topMetrics.length > 0 && (
        <ul className="health-service-metrics">
          {topMetrics.map((m) => (
            <li key={m.key}>
              <span>{m.label}</span>
              <strong>
                {m.value ?? '—'}
                {m.unit ? ` ${m.unit}` : ''}
              </strong>
            </li>
          ))}
        </ul>
      )}
      {service.error_message && (
        <p className="pc-health-error" role="status">
          {service.error_message}
        </p>
      )}
    </article>
  )
}
