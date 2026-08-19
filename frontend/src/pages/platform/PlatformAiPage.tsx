import { useEffect, useMemo, useState } from 'react'
import { api } from '../../api'
import { useAuth } from '../../auth'
import { EmptyState, ErrorState, ProgressBar, Skeleton, UiBadge } from '../../ui/UiStates'

export default function PlatformAiPage() {
  const { token } = useAuth()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [usage, setUsage] = useState<
    Array<{
      execution_id: string
      organization_id: number
      task_name: string
      provider: string
      model: string
      total_tokens?: number | null
      estimated_cost?: number | null
      currency?: string | null
    }>
  >([])
  const [executionsFailed, setExecutionsFailed] = useState(0)

  async function load() {
    if (!token) return
    setLoading(true)
    setError('')
    try {
      const [u, ex] = await Promise.all([
        api.platformAiUsage(token, { page: 1, page_size: 50 }),
        api.platformAiExecutions(token, { status: 'failed', page: 1, page_size: 1 }),
      ])
      setUsage(u.usage || [])
      setExecutionsFailed(ex.total || 0)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'API IA indisponible')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [token])

  const totals = useMemo(() => {
    const tokens = usage.reduce((s, r) => s + Number(r.total_tokens || 0), 0)
    const cost = usage.reduce((s, r) => s + Number(r.estimated_cost || 0), 0)
    const models = new Set(usage.map((r) => r.model).filter(Boolean))
    return { tokens, cost, models: models.size }
  }, [usage])

  return (
    <>
      <div className="platform-title">
        <span>IA</span>
        <h1>Consommation & exécutions</h1>
        <p>Tokens, coûts, modèles — API `/platform/ai/*` (aucune logique locale).</p>
      </div>
      {loading ? <Skeleton rows={5} /> : null}
      {error ? <ErrorState message={error} onRetry={() => void load()} /> : null}
      {!loading && !error ? (
        <>
          <div className="platform-stats">
            <article>
              <span>Tokens (échantillon)</span>
              <strong>{totals.tokens}</strong>
            </article>
            <article>
              <span>Coût estimé</span>
              <strong>{totals.cost.toFixed(4)}</strong>
            </article>
            <article>
              <span>Modèles</span>
              <strong>{totals.models}</strong>
            </article>
            <article>
              <span>Erreurs</span>
              <strong>
                {executionsFailed} <UiBadge tone="danger">failed</UiBadge>
              </strong>
            </article>
          </div>
          <ProgressBar
            value={executionsFailed ? Math.min(100, executionsFailed * 5) : 5}
            label="Pression erreurs (indicatif)"
          />
          {usage.length === 0 ? (
            <EmptyState title="Aucune consommation" description="Pas d’usage IA sur la période." />
          ) : (
            <div className="platform-table-wrap" style={{ marginTop: '1rem' }}>
              <table className="platform-table">
                <thead>
                  <tr>
                    <th>Org</th>
                    <th>Tâche</th>
                    <th>Provider</th>
                    <th>Modèle</th>
                    <th>Tokens</th>
                    <th>Coût</th>
                  </tr>
                </thead>
                <tbody>
                  {usage.map((r) => (
                    <tr key={r.execution_id}>
                      <td>{r.organization_id}</td>
                      <td>{r.task_name}</td>
                      <td>{r.provider}</td>
                      <td>{r.model}</td>
                      <td>{r.total_tokens ?? '—'}</td>
                      <td>
                        {r.estimated_cost != null
                          ? `${r.estimated_cost} ${r.currency || ''}`
                          : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      ) : null}
    </>
  )
}
