import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type PlatformOrganization } from '../../api'
import { useAuth } from '../../auth'
import { EmptyState, ErrorState, Skeleton, UiBadge } from '../../ui/UiStates'

/** Mode Support : erreurs, logs, quotas — sans accès comptable. */
export default function PlatformSupportPage() {
  const { token } = useAuth()
  const [orgs, setOrgs] = useState<PlatformOrganization[]>([])
  const [selected, setSelected] = useState<number | null>(null)
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null)
  const [incidents, setIncidents] = useState(0)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!token) return
    Promise.all([
      api.platformOrganizations(token),
      api.platformIncidents(token, { status: 'open' }),
    ])
      .then(([o, i]) => {
        setOrgs(o.organizations || [])
        setIncidents(i.total || 0)
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Support indisponible'))
      .finally(() => setLoading(false))
  }, [token])

  async function openOrg(id: number) {
    if (!token) return
    setSelected(id)
    setError('')
    try {
      const d = await api.platformOrgOpsDetail(id, token)
      setDetail(d as unknown as Record<string, unknown>)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Détail org indisponible')
      setDetail(null)
    }
  }

  return (
    <>
      <div className="platform-title">
        <span>Support</span>
        <h1>Mode Support</h1>
        <p>
          Ouvrir une organisation, quotas, erreurs et logs —{' '}
          <strong>sans données comptables</strong>.
        </p>
      </div>
      <div className="platform-stats">
        <article>
          <span>Incidents ouverts</span>
          <strong>{incidents}</strong>
        </article>
        <article>
          <span>Accès compta</span>
          <strong>
            <UiBadge tone="ok">bloqué</UiBadge>
          </strong>
        </article>
      </div>
      <p className="muted">
        Liens utiles : <Link to="/elfadmin/logs">Logs</Link> ·{' '}
        <Link to="/elfadmin/system-health">Santé</Link> ·{' '}
        <Link to="/elfadmin/incidents">Incidents</Link>
      </p>
      {loading ? <Skeleton rows={4} /> : null}
      {error ? <ErrorState message={error} /> : null}
      {!loading ? (
        <div className="platform-table-wrap">
          <table className="platform-table">
            <thead>
              <tr>
                <th>Organisation</th>
                <th>Statut</th>
                <th>Plan</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {orgs.map((o) => (
                <tr key={o.id}>
                  <td>
                    {o.name} <span className="muted">#{o.id}</span>
                  </td>
                  <td>{o.platform_status || 'active'}</td>
                  <td>{o.subscription?.plan || o.subscription?.status || '—'}</td>
                  <td>
                    <button type="button" className="btn secondary btn-sm" onClick={() => void openOrg(o.id)}>
                      Ouvrir
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      {selected && detail ? (
        <section className="panel" style={{ marginTop: '1rem' }}>
          <h2>
            Org #{selected} — ops (sans compta){' '}
            <UiBadge tone="warn">support</UiBadge>
          </h2>
          <pre className="platform-pre">
            {JSON.stringify(
              {
                organization: detail.organization,
                counts: detail.counts,
                billing: detail.billing,
                support_links: detail.support_links,
              },
              null,
              2,
            )}
          </pre>
        </section>
      ) : null}
      {!loading && orgs.length === 0 ? <EmptyState title="Aucune organisation" /> : null}
    </>
  )
}
