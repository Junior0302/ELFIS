import { useEffect, useState } from 'react'
import { api } from '../../api'
import { useAuth } from '../../auth'
import { EmptyState, ErrorState, Skeleton, UiBadge } from '../../ui/UiStates'

/** Configuration lecture seule — plans billing + email status (API existantes). */
export default function PlatformConfigurationPage() {
  const { token } = useAuth()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [plans, setPlans] = useState<Array<Record<string, unknown>>>([])
  const [email, setEmail] = useState<Record<string, unknown> | null>(null)

  useEffect(() => {
    if (!token) return
    Promise.all([api.platformBillingPlans(token), api.platformEmailStatus(token)])
      .then(([p, e]) => {
        setPlans(p.plans || [])
        setEmail(e)
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Configuration indisponible'))
      .finally(() => setLoading(false))
  }, [token])

  return (
    <>
      <div className="platform-title">
        <span>Configuration</span>
        <h1>Plans, emails, variables publiques</h1>
        <p>
          Lecture des registres backend — aucune mutation locale.{' '}
          <UiBadge tone="warn">pas de feature-flag API dédiée</UiBadge>
        </p>
      </div>
      {loading ? <Skeleton rows={5} /> : null}
      {error ? <ErrorState message={error} /> : null}
      {!loading && !error ? (
        <div className="ui-card-grid">
          <section className="panel">
            <h2>Plans billing</h2>
            {plans.length === 0 ? (
              <EmptyState title="Aucun plan" />
            ) : (
              <ul className="platform-service-list">
                {plans.map((p, i) => (
                  <li key={String(p.code || p.id || i)}>
                    <strong>{String(p.name || p.code || 'Plan')}</strong>
                    <span className="muted"> · {JSON.stringify(p).slice(0, 120)}…</span>
                  </li>
                ))}
              </ul>
            )}
          </section>
          <section className="panel">
            <h2>Email status</h2>
            <pre className="platform-pre">{JSON.stringify(email, null, 2)}</pre>
          </section>
        </div>
      ) : null}
    </>
  )
}
