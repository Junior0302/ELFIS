import { useEffect, useMemo, useState } from 'react'
import { api, type PlatformIncident } from '../../api'
import { useAuth } from '../../auth'
import { EmptyState, ErrorState, Skeleton, UiBadge } from '../../ui/UiStates'

type SevFilter = 'all' | string
type StatusFilter = 'all' | string

function severityTone(sev: string): 'neutral' | 'ok' | 'warn' | 'danger' {
  const s = sev.toLowerCase()
  if (s.includes('critical') || s.includes('high')) return 'danger'
  if (s.includes('medium') || s.includes('warn')) return 'warn'
  if (s.includes('low') || s.includes('info')) return 'ok'
  return 'neutral'
}

export default function PlatformIncidentsPage() {
  const { token } = useAuth()
  const [items, setItems] = useState<PlatformIncident[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [note, setNote] = useState('')
  const [busyId, setBusyId] = useState<string | null>(null)
  const [sevFilter, setSevFilter] = useState<SevFilter>('all')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [serviceFilter, setServiceFilter] = useState('all')
  const [q, setQ] = useState('')

  const reload = () => {
    if (!token) return Promise.resolve()
    setLoading(true)
    return api
      .platformIncidents(token)
      .then((r) => setItems(r.incidents))
      .catch((reason) => setError(reason instanceof Error ? reason.message : 'Incidents indisponibles'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    void reload()
  }, [token])

  const services = useMemo(() => {
    const set = new Set(items.map((i) => i.incident_type).filter(Boolean))
    return Array.from(set).sort()
  }, [items])

  const filtered = useMemo(() => {
    return items.filter((i) => {
      if (sevFilter !== 'all' && i.severity.toLowerCase() !== sevFilter.toLowerCase()) return false
      if (statusFilter !== 'all' && i.status.toLowerCase() !== statusFilter.toLowerCase()) return false
      if (serviceFilter !== 'all' && i.incident_type !== serviceFilter) return false
      if (q.trim()) {
        const hay = `${i.title} ${i.summary} ${i.incident_type}`.toLowerCase()
        if (!hay.includes(q.trim().toLowerCase())) return false
      }
      return true
    })
  }, [items, sevFilter, statusFilter, serviceFilter, q])

  const act = async (id: string, action: 'acknowledge' | 'resolve' | 'ignore') => {
    if (!token) return
    if (note.trim().length < 3) {
      setError('Note obligatoire (min. 3 caractères)')
      return
    }
    if (!window.confirm(`Confirmer l’action ${action} ?`)) return
    setBusyId(id)
    try {
      await api.platformIncidentAction(id, action, note.trim(), token)
      setNote('')
      setError('')
      await reload()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Échec')
    } finally {
      setBusyId(null)
    }
  }

  if (loading && items.length === 0) {
    return (
      <div className="pc-page">
        <Skeleton rows={5} />
      </div>
    )
  }

  if (error && items.length === 0) {
    return (
      <div className="pc-page">
        <ErrorState message={error} onRetry={() => void reload()} />
      </div>
    )
  }

  return (
    <div className="pc-page">
      <p className="pc-lede">
        Dead letters et échecs agrégés — actions acknowledge / resolve / ignore auditées côté API.
      </p>
      {error && <div className="platform-alert">{error}</div>}

      <div className="pc-filter-bar pc-filter-bar-wrap">
        <label className="pc-field">
          <span>Recherche</span>
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Titre, type…" />
        </label>
        <label className="pc-field">
          <span>Criticité</span>
          <select value={sevFilter} onChange={(e) => setSevFilter(e.target.value)}>
            <option value="all">Toutes</option>
            {[...new Set(items.map((i) => i.severity))].map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label className="pc-field">
          <span>Statut</span>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="all">Tous</option>
            {[...new Set(items.map((i) => i.status))].map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label className="pc-field">
          <span>Type / service</span>
          <select value={serviceFilter} onChange={(e) => setServiceFilter(e.target.value)}>
            <option value="all">Tous</option>
            {services.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label className="pc-field pc-field-grow">
          <span>Note d’action</span>
          <input
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Obligatoire pour Ack / Résoudre / Ignorer"
          />
        </label>
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          title="Aucun incident"
          description={items.length ? 'Aucun résultat pour ces filtres.' : 'File d’incidents vide.'}
        />
      ) : (
        <div className="platform-table-wrap pc-table-shell">
          <table className="platform-table pc-table">
            <thead>
              <tr>
                <th>Gravité</th>
                <th>Type</th>
                <th>Titre / message</th>
                <th>Org</th>
                <th>Statut</th>
                <th>Dernière occurrence</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((i) => (
                <tr key={i.incident_id}>
                  <td>
                    <UiBadge tone={severityTone(i.severity)}>{i.severity}</UiBadge>
                  </td>
                  <td>{i.incident_type}</td>
                  <td>
                    <strong>{i.title}</strong>
                    <p className="pc-table-sub">{i.summary || '—'}</p>
                  </td>
                  <td>{i.organization_id ?? '—'}</td>
                  <td>
                    <UiBadge tone="neutral">{i.status}</UiBadge>
                  </td>
                  <td>
                    {i.last_seen_at
                      ? new Date(i.last_seen_at).toLocaleString('fr-FR')
                      : 'Donnée indisponible'}
                  </td>
                  <td className="pc-table-actions">
                    <button
                      type="button"
                      className="pc-btn pc-btn-ghost"
                      disabled={busyId === i.incident_id}
                      onClick={() => void act(i.incident_id, 'acknowledge')}
                    >
                      Ack
                    </button>
                    <button
                      type="button"
                      className="pc-btn pc-btn-ghost"
                      disabled={busyId === i.incident_id}
                      onClick={() => void act(i.incident_id, 'resolve')}
                    >
                      Résoudre
                    </button>
                    <button
                      type="button"
                      className="pc-btn pc-btn-ghost"
                      disabled={busyId === i.incident_id}
                      onClick={() => void act(i.incident_id, 'ignore')}
                    >
                      Ignorer
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
