import { useEffect, useState } from 'react'
import { api } from '../../api'
import { useAuth } from '../../auth'

export default function PlatformObservabilityPage() {
  const { token } = useAuth()
  const [metrics, setMetrics] = useState<Record<string, unknown> | null>(null)
  const [health, setHealth] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) return
    Promise.all([api.platformObservabilityMetrics(token), api.platformObservabilityHealth(token)])
      .then(([m, h]) => {
        setMetrics(m.metrics)
        setHealth(h)
      })
      .catch((reason) => setError(reason instanceof Error ? reason.message : 'Observabilité indisponible'))
  }, [token])

  const counters = (metrics?.counters || {}) as Record<string, Array<{ value: number }>>
  const httpCount = (counters.http_requests_total || []).reduce((a, c) => a + (c.value || 0), 0)
  const errors = (counters.http_errors_total || []).reduce((a, c) => a + (c.value || 0), 0)
  const rateHits = (counters.http_rate_limit_hits || []).reduce((a, c) => a + (c.value || 0), 0)

  return (
    <>
      <div className="platform-title">
        <h1>Observabilité</h1>
        <p>Requêtes, erreurs, durée et santé modules — métriques mémoire V1.</p>
      </div>
      {error && <div className="platform-alert">{error}</div>}
      <div className="platform-stats">
        <article>
          <span>Requêtes HTTP</span>
          <strong>{httpCount}</strong>
        </article>
        <article>
          <span>Erreurs 5xx</span>
          <strong>{errors}</strong>
        </article>
        <article>
          <span>Rate limits</span>
          <strong>{rateHits}</strong>
        </article>
        <article>
          <span>Ready</span>
          <strong>{String((health as { status?: string } | null)?.status || '—')}</strong>
        </article>
      </div>
      {health && (
        <pre className="platform-pre" style={{ whiteSpace: 'pre-wrap', fontSize: 12 }}>
          {JSON.stringify(health, null, 2)}
        </pre>
      )}
    </>
  )
}
