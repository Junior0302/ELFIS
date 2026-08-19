import { useCallback, useEffect, useMemo, useState } from 'react'
import { useAuth } from '../../auth'
import { developerApi } from '../../services/developerApi'
import { api } from '../../api'
import { getSystemLogs } from '../../services/systemHealthApi'
import { getAuditEvents } from '../../services/auditApi'
import { DevError, DevLoading, DevPage, DevUnavailable, StatusBadge } from './devUi'
import { EmptyState } from '../../ui/UiStates'

export function DeveloperServicesPage() {
  const { token } = useAuth()
  const [items, setItems] = useState<Array<Record<string, unknown>>>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(() => {
    if (!token) return
    setLoading(true)
    developerApi
      .services(token)
      .then((r) => setItems(r.services))
      .catch((e) => setError(e instanceof Error ? e.message : 'Services indisponibles'))
      .finally(() => setLoading(false))
  }, [token])

  useEffect(() => {
    load()
  }, [load])

  if (loading) return <DevLoading />
  if (error) return <DevError message={error} onRetry={load} />

  return (
    <DevPage title="Service map">
      <p className="dev-lede">États issus de /platform/health/services (agrégateur developer).</p>
      <div className="dev-service-grid">
        {items.map((s) => (
          <article key={String(s.service)} className="dev-card">
            <header>
              <strong>{String(s.service)}</strong>
              <StatusBadge status={String(s.status || 'unknown')} />
            </header>
            <p>{String(s.message || '—')}</p>
            <dl className="dev-dl">
              <div>
                <dt>Latence</dt>
                <dd>{s.latency_ms != null ? `${s.latency_ms} ms` : 'Donnée indisponible'}</dd>
              </div>
              <div>
                <dt>Version</dt>
                <dd>{s.version != null ? String(s.version) : 'Donnée indisponible'}</dd>
              </div>
              <div>
                <dt>Requêtes / échecs</dt>
                <dd>Donnée indisponible</dd>
              </div>
            </dl>
          </article>
        ))}
      </div>
    </DevPage>
  )
}

export function DeveloperApiPage() {
  const { token } = useAuth()
  const [routes, setRoutes] = useState<Array<Record<string, unknown>>>([])
  const [q, setQ] = useState('')
  const [method, setMethod] = useState('all')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!token) return
    developerApi
      .routes(token)
      .then((r) => setRoutes(r.routes))
      .catch((e) => setError(e instanceof Error ? e.message : 'Routes indisponibles'))
      .finally(() => setLoading(false))
  }, [token])

  const filtered = useMemo(() => {
    return routes.filter((r) => {
      const methods = (r.methods as string[]) || []
      if (method !== 'all' && !methods.includes(method)) return false
      if (q && !String(r.path).toLowerCase().includes(q.toLowerCase())) return false
      return true
    })
  }, [routes, q, method])

  if (loading) return <DevLoading />
  if (error) return <DevError message={error} />

  return (
    <DevPage title="API Explorer">
      <p className="dev-lede">
        Catalogue FastAPI lecture seule — aucune exécution de routes sensibles depuis cette UI.
      </p>
      <div className="dev-filters">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Filtrer le chemin…" />
        <select value={method} onChange={(e) => setMethod(e.target.value)}>
          <option value="all">Toutes méthodes</option>
          {['GET', 'POST', 'PUT', 'PATCH', 'DELETE'].map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </div>
      <div className="dev-table-wrap">
        <table className="dev-table">
          <thead>
            <tr>
              <th>Méthodes</th>
              <th>Chemin</th>
              <th>Tags</th>
              <th>Sensible</th>
            </tr>
          </thead>
          <tbody>
            {filtered.slice(0, 300).map((r) => (
              <tr key={`${r.path}-${(r.methods as string[]).join()}`}>
                <td>{(r.methods as string[]).join(', ')}</td>
                <td>
                  <code>{String(r.path)}</code>
                </td>
                <td>{((r.tags as string[]) || []).join(', ') || '—'}</td>
                <td>{r.sensitive_path ? 'oui' : 'non'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="dev-meta">{filtered.length} routes (max 300 affichées)</p>
    </DevPage>
  )
}

export function DeveloperWorkersPage() {
  return (
    <DevUnavailable
      title="Workers"
      reason="Aucune API de listing / restart / pause / drain des workers n’existe encore. Les flags event_worker / job_worker sont visibles dans Diagnostics et Config."
    />
  )
}

export function DeveloperJobsPage() {
  const { token } = useAuth()
  const [jobs, setJobs] = useState<Array<Record<string, unknown>>>([])
  const [total, setTotal] = useState(0)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<string | null>(null)

  const load = useCallback(() => {
    if (!token) return
    setLoading(true)
    api
      .platformJobs(token, { status: status || undefined, page_size: 50 })
      .then((r) => {
        setJobs(r.jobs)
        setTotal(r.total)
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Jobs indisponibles'))
      .finally(() => setLoading(false))
  }, [token, status])

  useEffect(() => {
    load()
  }, [load])

  const act = async (id: string, action: 'retry' | 'cancel') => {
    if (!token) return
    if (!window.confirm(`Confirmer ${action} du job ${id} ?`)) return
    setBusy(id)
    try {
      if (action === 'retry') {
        await api.platformJobManualRetry(id, 'developer_cockpit', token)
      } else {
        await api.platformJobManualCancel(id, 'developer_cockpit', token)
      }
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Action échouée')
    } finally {
      setBusy(null)
    }
  }

  if (loading && !jobs.length) return <DevLoading />

  return (
    <DevPage title="Jobs & Queues">
      <p className="dev-lede">
        Source : /platform/jobs — payloads déjà sanitizés côté API. Actions retry/cancel confirmées.
      </p>
      {error && <div className="dev-alert">{error}</div>}
      <div className="dev-filters">
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">Tous statuts</option>
          {['pending', 'processing', 'failed', 'dead_letter', 'completed', 'cancelled'].map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <button type="button" className="dev-btn" onClick={load}>
          Actualiser
        </button>
      </div>
      {!jobs.length ? (
        <EmptyState title="Aucun job" description="File vide pour ce filtre." />
      ) : (
        <div className="dev-table-wrap">
          <table className="dev-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Type</th>
                <th>Statut</th>
                <th>Queue</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((j) => {
                const id = String(j.job_id || j.id || '')
                return (
                  <tr key={id}>
                    <td>
                      <code>{id.slice(0, 12)}</code>
                    </td>
                    <td>{String(j.job_name || j.name || '—')}</td>
                    <td>
                      <StatusBadge status={String(j.status || 'unknown')} />
                    </td>
                    <td>{String(j.queue_name || '—')}</td>
                    <td className="dev-actions">
                      <button
                        type="button"
                        className="dev-btn ghost"
                        disabled={busy === id}
                        onClick={() => void act(id, 'retry')}
                      >
                        Retry
                      </button>
                      <button
                        type="button"
                        className="dev-btn ghost"
                        disabled={busy === id}
                        onClick={() => void act(id, 'cancel')}
                      >
                        Cancel
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
      <p className="dev-meta">Total API : {total}</p>
    </DevPage>
  )
}

export function DeveloperEventsPage() {
  const { token } = useAuth()
  const [items, setItems] = useState<Array<Record<string, unknown>>>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!token) return
    api
      .platformEvents(token, { page_size: 100 })
      .then((r) => setItems(r.events || []))
      .catch((e) => setError(e instanceof Error ? e.message : 'Events indisponibles'))
      .finally(() => setLoading(false))
  }, [token])

  if (loading) return <DevLoading />
  if (error) return <DevError message={error} />

  return (
    <DevPage title="Event Bus">
      <p className="dev-lede">Événements plateforme — payload redacted côté API.</p>
      <div className="dev-table-wrap">
        <table className="dev-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Type</th>
              <th>Statut</th>
              <th>Org</th>
            </tr>
          </thead>
          <tbody>
            {items.slice(0, 100).map((e) => (
              <tr key={String(e.event_id || e.id)}>
                <td>
                  <code>{String(e.event_id || e.id).slice(0, 12)}</code>
                </td>
                <td>{String(e.event_name || e.name || '—')}</td>
                <td>
                  <StatusBadge status={String(e.status || 'unknown')} />
                </td>
                <td>{e.organization_id != null ? String(e.organization_id) : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </DevPage>
  )
}

export function DeveloperLogsPage() {
  const { token } = useAuth()
  const [entries, setEntries] = useState<Array<Record<string, unknown>>>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!token) return
    getSystemLogs(token, { limit: 100 })
      .then((r) => setEntries((r.entries || []) as unknown as Array<Record<string, unknown>>))
      .catch((e) => setError(e instanceof Error ? e.message : 'Logs indisponibles'))
      .finally(() => setLoading(false))
  }, [token])

  if (loading) return <DevLoading />
  if (error) return <DevError message={error} />

  return (
    <DevPage title="Logs techniques">
      <p className="dev-lede">
        Source /admin/system/logs — pagination serveur. Ne pas coller de secrets dans la recherche.
      </p>
      <div className="dev-table-wrap">
        <table className="dev-table">
          <thead>
            <tr>
              <th>Horodatage</th>
              <th>Niveau</th>
              <th>Service</th>
              <th>Message</th>
              <th>correlation</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((e) => (
              <tr key={String(e.log_id || `${e.timestamp}-${e.message}`)}>
                <td>{String(e.timestamp || '—')}</td>
                <td>{String(e.level || '—')}</td>
                <td>{String(e.service_id || '—')}</td>
                <td>{String(e.message || '—')}</td>
                <td>
                  <code>{String(e.correlation_id || '—')}</code>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </DevPage>
  )
}

export function DeveloperTracesPage() {
  return (
    <DevUnavailable
      title="Traces"
      reason="Pas d’API de timeline cross-services unifiée. Utilisez correlation_id / request_id dans Logs, Jobs et Audit pour reconstruire manuellement une chaîne."
    />
  )
}

export function DeveloperDatabasePage() {
  const { token } = useAuth()
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null)
  const [collisions, setCollisions] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) return
    Promise.all([developerApi.databaseSummary(token), developerApi.indexCollisions(token)])
      .then(([s, c]) => {
        setSummary(s)
        setCollisions(c)
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Database indisponible'))
  }, [token])

  if (error) return <DevError message={error} />
  if (!summary) return <DevLoading />

  return (
    <DevPage title="Base de données">
      <p className="dev-lede">Lecture seule — pas de console SQL, pas de données métier.</p>
      <div className="dev-kpi-grid">
        <article className="dev-kpi">
          <span>Moteur</span>
          <strong>{String(summary.engine)}</strong>
        </article>
        <article className="dev-kpi">
          <span>Statut</span>
          <strong>
            <StatusBadge status={String(summary.status)} />
          </strong>
        </article>
        <article className="dev-kpi">
          <span>Latence</span>
          <strong>{summary.latency_ms != null ? `${summary.latency_ms} ms` : '—'}</strong>
        </article>
        <article className="dev-kpi">
          <span>Tables (metadata)</span>
          <strong>
            {summary.table_count_metadata != null
              ? String(summary.table_count_metadata)
              : 'Donnée indisponible'}
          </strong>
        </article>
      </div>
      <section className="dev-section">
        <h2>Collisions d’index (scan statique)</h2>
        <p>
          Index nommés : {String(collisions?.total_named_indexes ?? '—')} — doublons :{' '}
          {String(collisions?.duplicate_index_names ?? '—')}
        </p>
        {collisions && Number(collisions.duplicate_index_names) > 0 ? (
          <pre className="dev-pre">{JSON.stringify(collisions.collisions, null, 2)}</pre>
        ) : (
          <p>Aucun doublon détecté.</p>
        )}
      </section>
    </DevPage>
  )
}

export function DeveloperCachePage() {
  return (
    <DevUnavailable title="Cache" reason="Aucun backend cache exposé pour le Developer Cockpit V1." />
  )
}

export function DeveloperStoragePage() {
  return (
    <DevPage title="Storage">
      <p className="dev-lede">
        Réutiliser la page Admin Storage pour les détails provider / migrations / integrity.
      </p>
      <p>
        <a className="dev-btn" href="/elfadmin/storage">
          Ouvrir Storage (Admin)
        </a>
      </p>
    </DevPage>
  )
}

export function DeveloperSearchPage() {
  return (
    <DevPage title="Search">
      <p className="dev-lede">Ops Search disponibles via APIs platform search (reindex inclus).</p>
      <p>
        <a className="dev-btn" href="/elfadmin/documents">
          Documents / Search Admin
        </a>
      </p>
    </DevPage>
  )
}

export function DeveloperAiPage() {
  const { token } = useAuth()
  const [usage, setUsage] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) return
    api
      .platformAiUsage(token)
      .then((r) => setUsage(r as unknown as Record<string, unknown>))
      .catch((e) => setError(e instanceof Error ? e.message : 'IA indisponible'))
  }, [token])

  return (
    <DevPage title="IA (technique)">
      <p className="dev-lede">Usage agrégé — clés API jamais exposées.</p>
      {error && <div className="dev-alert">{error}</div>}
      {usage ? (
        <pre className="dev-pre">{JSON.stringify(usage, null, 2).slice(0, 4000)}</pre>
      ) : (
        !error && <DevLoading />
      )}
    </DevPage>
  )
}

export function DeveloperNotificationsPage() {
  return (
    <DevPage title="Notifications & Delivery">
      <p className="dev-lede">Identifiants SMTP / Brevo masqués. Voir aussi Diagnostics.</p>
      <p>
        <a className="dev-btn" href="/elfadmin/notifications">
          Notifications Admin
        </a>
      </p>
    </DevPage>
  )
}

export function DeveloperFeatureFlagsPage() {
  return (
    <DevUnavailable
      title="Feature Flags"
      reason="Aucune API feature-flags sécurisée n’existe. Page lecture seule volontairement vide."
    />
  )
}

export function DeveloperConfigPage() {
  const { token } = useAuth()
  const [data, setData] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) return
    developerApi
      .configStatus(token)
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : 'Config indisponible'))
  }, [token])

  if (error) return <DevError message={error} />
  if (!data) return <DevLoading />

  const secrets = (data.secrets || []) as Array<{ key: string; status: string }>
  const pub = (data.public || {}) as Record<string, unknown>

  return (
    <DevPage title="Configurations techniques">
      <p className="dev-lede">{String(data.note || '')}</p>
      <h2>Public</h2>
      <pre className="dev-pre">{JSON.stringify(pub, null, 2)}</pre>
      <h2>Secrets (statut uniquement)</h2>
      <div className="dev-table-wrap">
        <table className="dev-table">
          <thead>
            <tr>
              <th>Clé</th>
              <th>Statut</th>
            </tr>
          </thead>
          <tbody>
            {secrets.map((s) => (
              <tr key={s.key}>
                <td>
                  <code>{s.key}</code>
                </td>
                <td>
                  <StatusBadge status={s.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </DevPage>
  )
}

export function DeveloperDiagnosticsPage() {
  const { token } = useAuth()
  const [checks, setChecks] = useState<Array<Record<string, unknown>>>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const run = () => {
    if (!token) return
    setLoading(true)
    setError('')
    developerApi
      .diagnostics(token)
      .then((r) => setChecks(r.checks))
      .catch((e) => setError(e instanceof Error ? e.message : 'Diagnostics KO'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    run()
  }, [token])

  return (
    <DevPage title="Diagnostics">
      <p className="dev-lede">Checks sûrs — aucune mutation métier.</p>
      <button type="button" className="dev-btn" onClick={run} disabled={loading}>
        {loading ? 'Exécution…' : 'Relancer'}
      </button>
      {error && <div className="dev-alert">{error}</div>}
      <div className="dev-table-wrap">
        <table className="dev-table">
          <thead>
            <tr>
              <th>Check</th>
              <th>OK</th>
              <th>Message</th>
              <th>ms</th>
              <th>Reco</th>
            </tr>
          </thead>
          <tbody>
            {checks.map((c) => (
              <tr key={String(c.name)}>
                <td>{String(c.name)}</td>
                <td>{c.ok ? 'oui' : 'non'}</td>
                <td>{String(c.message)}</td>
                <td>{c.duration_ms != null ? String(c.duration_ms) : '—'}</td>
                <td>{String(c.recommendation || '—')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </DevPage>
  )
}

export function DeveloperAuditPage() {
  const { token } = useAuth()
  const [items, setItems] = useState<Array<Record<string, unknown>>>([])
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) return
    getAuditEvents(token, { limit: 50, offset: 0, hours: 24 })
      .then((r) => setItems((r.items || []) as unknown as Array<Record<string, unknown>>))
      .catch((e) => setError(e instanceof Error ? e.message : 'Audit indisponible'))
  }, [token])

  if (error) return <DevError message={error} />

  return (
    <DevPage title="Audit technique">
      <p className="dev-lede">
        Journal /admin/audit/events (24h). IP déjà redacted côté moteur d’audit.
      </p>
      {!items.length && !error ? (
        <DevLoading />
      ) : (
        <div className="dev-table-wrap">
          <table className="dev-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Action</th>
                <th>Acteur</th>
                <th>Résultat</th>
              </tr>
            </thead>
            <tbody>
              {items.map((e) => (
                <tr key={String(e.id)}>
                  <td>{String(e.created_at || e.timestamp || '—')}</td>
                  <td>{String(e.action || '—')}</td>
                  <td>{String(e.actor_email || e.actor_user_id || '—')}</td>
                  <td>{String(e.status || (e.success ? 'success' : '—'))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </DevPage>
  )
}
