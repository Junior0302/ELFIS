import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../../auth'
import { financialApi, formatEuro, type PlatformFinancialOverview } from '../../services/financialApi'
import { EmptyState, ErrorState, Skeleton, UiBadge } from '../../ui/UiStates'

export default function PlatformFinancePage() {
  const { token } = useAuth()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [data, setData] = useState<PlatformFinancialOverview | null>(null)

  const load = useCallback(async () => {
    if (!token) return
    setLoading(true)
    setError('')
    try {
      setData(await financialApi.platformOverview(token))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'API financial plateforme indisponible')
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    void load()
  }, [load])

  return (
    <>
      <div className="platform-title">
        <span>Finance</span>
        <h1>Santé financière plateforme</h1>
        <p>
          Score de santé moyen, alertes, organisations sans synchronisation et statistiques
          globales — API `/platform/financial`.
        </p>
      </div>

      {loading ? <Skeleton rows={6} /> : null}
      {error ? <ErrorState message={error} onRetry={() => void load()} /> : null}

      {!loading && !error && data ? (
        <>
          <div className="platform-toolbar">
            <UiBadge>
              {data.average_score != null ? `Score moyen ${data.average_score}/100` : 'score n/a'}
            </UiBadge>
            <UiBadge>{data.organizations_active} org. active(s)</UiBadge>
            <UiBadge>{data.organizations_setup} en configuration</UiBadge>
            <UiBadge>{data.organizations_without_sync} sans synchronisation</UiBadge>
            <UiBadge>{data.critical_alerts} alerte(s) critique(s)</UiBadge>
            <UiBadge>{data.warning_alerts} vigilance(s)</UiBadge>
            <UiBadge>{data.sync_errors} erreur(s) de sync</UiBadge>
            <button type="button" className="btn secondary" onClick={() => void load()}>
              Rafraîchir
            </button>
          </div>

          {data.organizations.length === 0 ? (
            <EmptyState
              title="Aucune organisation"
              description="Aucune donnée financière disponible."
            />
          ) : (
            <div className="platform-table-wrap">
              <table className="platform-table">
                <thead>
                  <tr>
                    <th>Organisation</th>
                    <th>Score</th>
                    <th>Trésorerie</th>
                    <th>CA</th>
                    <th>Synchronisation</th>
                    <th>Alertes</th>
                  </tr>
                </thead>
                <tbody>
                  {data.organizations.map((org) => (
                    <tr key={org.organization_id}>
                      <td>
                        <strong>{org.name}</strong>
                      </td>
                      <td>
                        {org.state === 'setup' || org.score == null
                          ? 'Configuration'
                          : `${org.score} (${org.grade})`}
                      </td>
                      <td>{formatEuro(org.treasury)}</td>
                      <td>{formatEuro(org.revenue)}</td>
                      <td>{org.sync_status}</td>
                      <td>
                        {org.critical_alerts ? `${org.critical_alerts} critique(s) ` : ''}
                        {org.warning_alerts ? `${org.warning_alerts} vigilance(s)` : ''}
                        {!org.critical_alerts && !org.warning_alerts ? '—' : ''}
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
