import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../../auth'
import { bankingApi } from '../../services/bankingApi'
import { EmptyState, ErrorState, Skeleton, UiBadge } from '../../ui/UiStates'

type Overview = Awaited<ReturnType<typeof bankingApi.platformOverview>>

function fmtDate(value: unknown): string {
  if (!value) return '—'
  const d = new Date(String(value))
  return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleString('fr-FR')
}

export default function PlatformBankingPage() {
  const { token } = useAuth()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [data, setData] = useState<Overview | null>(null)

  const load = useCallback(async () => {
    if (!token) return
    setLoading(true)
    setError('')
    try {
      setData(await bankingApi.platformOverview(token))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'API banking plateforme indisponible')
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
        <span>Banking</span>
        <h1>Connexions bancaires plateforme</h1>
        <p>Connexions actives, erreurs, synchronisations, temps moyen et taux d'échec — API `/platform/banking`.</p>
      </div>

      {loading ? <Skeleton rows={6} /> : null}
      {error ? <ErrorState message={error} onRetry={() => void load()} /> : null}

      {!loading && !error && data ? (
        <>
          <div className="platform-toolbar">
            <UiBadge>{data.connections_active} connexion(s) active(s)</UiBadge>
            <UiBadge>{data.connections_error} en erreur</UiBadge>
            <UiBadge>{data.runs_total} sync</UiBadge>
            <UiBadge>{Math.round(data.failure_rate * 100)} % d'échec</UiBadge>
            <UiBadge>
              {data.avg_duration_ms != null ? `${Math.round(data.avg_duration_ms)} ms en moyenne` : 'durée n/a'}
            </UiBadge>
            <button type="button" className="btn secondary" onClick={() => void load()}>
              Rafraîchir
            </button>
          </div>

          <div className="platform-table-wrap">
            <table className="platform-table">
              <thead>
                <tr>
                  <th>Fournisseur</th>
                  <th>Connexions</th>
                  <th>Connectées</th>
                  <th>En erreur</th>
                </tr>
              </thead>
              <tbody>
                {data.by_provider.map((p) => (
                  <tr key={p.provider}>
                    <td>
                      <strong>{p.provider}</strong>
                    </td>
                    <td>{p.connections}</td>
                    <td>{p.connected}</td>
                    <td>{p.errors}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {data.recent_errors.length ? (
            <div className="platform-table-wrap">
              <table className="platform-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Org</th>
                    <th>Fournisseur</th>
                    <th>Tentatives</th>
                    <th>Erreur</th>
                  </tr>
                </thead>
                <tbody>
                  {data.recent_errors.map((e, i) => (
                    <tr key={String(e.run_id ?? i)}>
                      <td>{fmtDate(e.started_at)}</td>
                      <td>{String(e.organization_id ?? '—')}</td>
                      <td>{String(e.provider ?? '—')}</td>
                      <td>{String(e.attempt_count ?? '—')}</td>
                      <td>{String(e.error_message ?? '—')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState
              title="Aucune erreur récente"
              description="Toutes les synchronisations récentes ont abouti."
            />
          )}
        </>
      ) : null}

      {!loading && !error && data && data.connections_total === 0 ? (
        <EmptyState
          title="Aucune connexion bancaire"
          description="Aucune organisation n'a encore connecté de banque."
        />
      ) : null}
    </>
  )
}
