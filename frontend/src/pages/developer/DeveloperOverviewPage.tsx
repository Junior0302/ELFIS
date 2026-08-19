import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../auth'
import { developerApi } from '../../services/developerApi'
import { DevError, DevLoading, DevPage, StatusBadge } from './devUi'

export default function DeveloperOverviewPage() {
  const { token } = useAuth()
  const [data, setData] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(() => {
    if (!token) return
    setLoading(true)
    setError('')
    developerApi
      .overview(token)
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : 'Overview indisponible'))
      .finally(() => setLoading(false))
  }, [token])

  useEffect(() => {
    load()
  }, [load])

  if (loading && !data) return <DevLoading />
  if (error && !data) return <DevError message={error} onRetry={load} />
  if (!data) return null

  const dash = (data.dashboard || {}) as Record<string, unknown>
  const services = (data.services || []) as Array<Record<string, unknown>>
  const unavailable = (data.unavailable || {}) as Record<string, string>

  const kpis = [
    { label: 'Jobs pending', value: dash.jobs_pending },
    { label: 'Jobs running', value: dash.jobs_running },
    { label: 'Jobs failed', value: dash.jobs_failed },
    { label: 'Dead letters jobs', value: dash.jobs_dead_letter },
    { label: 'Events DL', value: dash.events_dead_letter },
    { label: 'Incidents ouverts', value: dash.incidents_open },
    { label: 'Orgs', value: dash.organizations_total },
    { label: 'Users', value: dash.users_total },
    { label: 'IA aujourd’hui', value: dash.ai_analyses_today },
    { label: 'Docs traités', value: dash.documents_processed_today },
    { label: 'Uptime (s)', value: data.uptime_seconds },
    { label: 'Latence overview (ms)', value: data.latency_ms },
  ]

  return (
    <DevPage title="Vue technique">
      <p className="dev-lede">
        Centre de supervision ELFIS Core — données API uniquement. Période agrégée :{' '}
        <strong>{String(data.period)}</strong>. Env : <strong>{String(data.environment)}</strong>.
      </p>
      {error && <div className="dev-alert">{error}</div>}

      <div className="dev-kpi-grid">
        {kpis.map((k) => (
          <article key={k.label} className="dev-kpi">
            <span>{k.label}</span>
            <strong>{k.value == null ? 'Donnée indisponible' : String(k.value)}</strong>
          </article>
        ))}
      </div>

      <section className="dev-section">
        <h2>Services (aperçu)</h2>
        <div className="dev-service-grid">
          {services.slice(0, 12).map((s) => (
            <article key={String(s.service)} className="dev-card">
              <header>
                <strong>{String(s.service)}</strong>
                <StatusBadge status={String(s.status || 'unknown')} />
              </header>
              <p>{String(s.message || '—')}</p>
            </article>
          ))}
        </div>
        <p>
          <Link to="/elfadmin/developer/services">Carte services complète →</Link>
        </p>
      </section>

      <section className="dev-section">
        <h2>Indisponibilités assumées</h2>
        <ul className="dev-list">
          {Object.entries(unavailable).map(([k, v]) => (
            <li key={k}>
              <strong>{k}</strong> — {v}
            </li>
          ))}
        </ul>
      </section>

      <p className="dev-meta">Généré à {String(data.generated_at)}</p>
    </DevPage>
  )
}
