import type { SystemAlert } from '../../types/systemHealth'

export default function HealthAlertPanel({ alerts }: { alerts: SystemAlert[] }) {
  if (!alerts.length) {
    return <p className="platform-alert platform-alert-ok">Aucune alerte active.</p>
  }
  return (
    <div className="health-alert-panel">
      {alerts.map((alert) => (
        <article key={alert.alert_id} className={`health-alert health-alert-${alert.severity}`}>
          <header>
            <span className={`platform-pill health-severity-${alert.severity}`}>{alert.severity}</span>
            <strong>{alert.title}</strong>
          </header>
          <p>{alert.message}</p>
          {alert.impact && (
            <p>
              <em>Impact :</em> {alert.impact}
            </p>
          )}
          {alert.recommendation && (
            <p>
              <em>Recommandation :</em> {alert.recommendation}
            </p>
          )}
          <footer>
            Début : {new Date(alert.started_at).toLocaleString('fr-FR')}
            {alert.service_id ? ` · ${alert.service_id}` : ''}
          </footer>
        </article>
      ))}
    </div>
  )
}
