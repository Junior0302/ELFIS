import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type PlatformOrganization } from '../../api'
import { useAuth } from '../../auth'
import { migrationApi, type MigrationSession } from '../../services/migrationApi'
import {
  smartMigrationApi,
  type SmartDashboard,
} from '../../services/smartMigrationApi'
import { EmptyState, ErrorState, ProgressBar, Skeleton } from '../../ui/UiStates'

export default function PlatformMigrationOpsPage() {
  const { token } = useAuth()
  const [orgs, setOrgs] = useState<PlatformOrganization[]>([])
  const [orgId, setOrgId] = useState<number | ''>('')
  const [sessions, setSessions] = useState<MigrationSession[]>([])
  const [dash, setDash] = useState<SmartDashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) return
    api
      .platformOrganizations(token)
      .then((r) => {
        setOrgs(r.organizations || [])
        if (r.organizations?.[0]) setOrgId(r.organizations[0].id)
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Orgs indisponibles'))
      .finally(() => setLoading(false))
  }, [token])

  async function loadOrg(id: number) {
    if (!token) return
    setError('')
    setLoading(true)
    try {
      const list = await migrationApi.listSessions(token, id)
      setSessions(list.items || [])
      const first = list.items?.[0]
      if (first) {
        const d = await smartMigrationApi.dashboard(token, id, first.id).catch(() => null)
        setDash(d)
      } else {
        setDash(null)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Migration API indisponible')
      setSessions([])
      setDash(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (typeof orgId === 'number') void loadOrg(orgId)
  }, [orgId, token])

  return (
    <>
      <div className="platform-title">
        <span>Migration</span>
        <h1>Suivi multi-organisations</h1>
        <p>Sessions, progression, ETA — APIs Migration Center existantes (contexte org).</p>
      </div>
      <div className="platform-toolbar">
        <label>
          Organisation{' '}
          <select
            value={orgId === '' ? '' : String(orgId)}
            onChange={(e) => setOrgId(e.target.value ? Number(e.target.value) : '')}
            aria-label="Organisation"
          >
            <option value="">—</option>
            {orgs.map((o) => (
              <option key={o.id} value={o.id}>
                {o.name} (#{o.id})
              </option>
            ))}
          </select>
        </label>
        <Link className="btn secondary" to="/migration">
          Ouvrir produit Migration
        </Link>
      </div>
      {loading ? <Skeleton rows={5} /> : null}
      {error ? (
        <ErrorState
          message={error}
          onRetry={() => typeof orgId === 'number' && void loadOrg(orgId)}
        />
      ) : null}
      {!loading && !error && sessions.length === 0 ? (
        <EmptyState title="Aucune session" description="Pas de migration pour cette organisation." />
      ) : null}
      {sessions.length > 0 ? (
        <div className="platform-table-wrap">
          <table className="platform-table">
            <thead>
              <tr>
                <th>Session</th>
                <th>Statut</th>
                <th>Mode</th>
                <th>Progression</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((s) => {
                const pct = (() => {
                  const p = s.progress
                  if (!p || typeof p !== 'object') return 0
                  if ('overall_percent' in p && typeof p.overall_percent === 'number') {
                    return p.overall_percent
                  }
                  return 0
                })()
                return (
                  <tr key={s.id}>
                    <td>
                      <code>{s.id.slice(0, 8)}</code>
                    </td>
                    <td>{s.status}</td>
                    <td>{s.mode}</td>
                    <td>
                      <ProgressBar value={pct} label={`${pct} %`} />
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      ) : null}
      {dash ? (
        <section className="panel" style={{ marginTop: '1rem' }}>
          <h2>Smart Migration</h2>
          <p className="muted">
            {dash.status} · {dash.documents_completed}/{dash.documents_total} · ETA{' '}
            {dash.eta_seconds ?? '—'}s · batches actifs {dash.active_batches}
          </p>
          <ProgressBar value={dash.progress_percent} label="Progression run" />
        </section>
      ) : null}
    </>
  )
}
