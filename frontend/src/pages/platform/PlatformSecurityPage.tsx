import { useEffect, useState } from 'react'
import { api } from '../../api'
import { useAuth } from '../../auth'

type SecurityEvent = {
  security_event_id: string
  event_type: string
  severity: string
  route?: string | null
  organization_id?: number | null
  request_id?: string | null
  created_at?: string | null
}

export default function PlatformSecurityPage() {
  const { token } = useAuth()
  const [events, setEvents] = useState<SecurityEvent[]>([])
  const [config, setConfig] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) return
    Promise.all([api.platformSecurityEvents(token), api.platformSecurityConfiguration(token)])
      .then(([ev, cfg]) => {
        setEvents(ev.events as SecurityEvent[])
        setConfig(cfg)
      })
      .catch((reason) => setError(reason instanceof Error ? reason.message : 'Sécurité indisponible'))
  }, [token])

  return (
    <>
      <div className="platform-title">
        <h1>Sécurité</h1>
        <p>Événements, protections actives et configuration (sans secrets).</p>
      </div>
      {error && <div className="platform-alert">{error}</div>}
      {config && (
        <div className="platform-stats">
          <article>
            <span>Environnement</span>
            <strong>{String((config as { environment?: string }).environment || '—')}</strong>
          </article>
          <article>
            <span>Issues</span>
            <strong>{Array.isArray((config as { issues?: unknown[] }).issues) ? (config as { issues: unknown[] }).issues.length : 0}</strong>
          </article>
        </div>
      )}
      <div className="platform-table-wrap">
        <table className="platform-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Type</th>
              <th>Sévérité</th>
              <th>Route</th>
              <th>Org</th>
              <th>Request</th>
            </tr>
          </thead>
          <tbody>
            {events.length === 0 ? (
              <tr>
                <td colSpan={6}>Aucun événement sécurité récent.</td>
              </tr>
            ) : (
              events.map((e) => (
                <tr key={e.security_event_id}>
                  <td>{e.created_at || '—'}</td>
                  <td>{e.event_type}</td>
                  <td>{e.severity}</td>
                  <td>{e.route || '—'}</td>
                  <td>{e.organization_id ?? '—'}</td>
                  <td>{e.request_id || '—'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </>
  )
}
