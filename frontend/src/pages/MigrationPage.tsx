import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import {
  canCancelStatus,
  canResumeStatus,
  migrationApi,
  progressPercent,
  type MigrationSession,
} from '../services/migrationApi'

const STATUS_LABEL: Record<string, string> = {
  draft: 'Brouillon',
  profile_completed: 'Profil renseigné',
  sources_selected: 'Sources choisies',
  awaiting_upload: 'Prêt pour dépôt',
  cancelled: 'Annulée',
  completed: 'Terminée',
  failed: 'Échouée',
}

const MODE_LABEL: Record<string, string> = {
  initial_migration: 'Migration initiale',
  one_time_import: 'Import ponctuel',
}

export default function MigrationPage() {
  const { token, orgId } = useAuth()
  const navigate = useNavigate()
  const [items, setItems] = useState<MigrationSession[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busyId, setBusyId] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!token || orgId == null) return
    setLoading(true)
    setError('')
    try {
      const data = await migrationApi.listSessions(token, orgId)
      setItems(data.items)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Impossible de charger les migrations')
    } finally {
      setLoading(false)
    }
  }, [token, orgId])

  useEffect(() => {
    void load()
  }, [load])

  async function startNew() {
    navigate('/migration/new')
  }

  async function resume(session: MigrationSession) {
    if (!token || orgId == null) return
    setBusyId(session.id)
    setError('')
    try {
      await migrationApi.resumeSession(token, orgId, session.id)
      navigate(`/migration/${session.id}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Reprise impossible')
    } finally {
      setBusyId(null)
    }
  }

  async function cancel(session: MigrationSession) {
    if (!token || orgId == null) return
    if (!window.confirm('Annuler cette session de migration ?')) return
    setBusyId(session.id)
    setError('')
    try {
      await migrationApi.cancelSession(token, orgId, session.id, session.version)
      await load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Annulation impossible')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Assistant de Migration</h2>
          <p>
            Préparez votre entreprise sur ComptaPilot : profil, sources, puis dépôt de données — sans
            import automatique.
          </p>
        </div>
        <button type="button" className="btn" onClick={() => void startNew()}>
          Commencer une migration
        </button>
      </div>

      {error ? <div className="panel form-error">{error}</div> : null}
      {loading ? <div className="loading">Chargement…</div> : null}

      {!loading && !items.length ? (
        <div className="panel empty">
          <p>Aucune session pour le moment.</p>
          <button type="button" className="btn" onClick={() => void startNew()}>
            Créer la première
          </button>
        </div>
      ) : null}

      {!loading && items.length > 0 ? (
        <div className="list">
          {items.map((s) => {
            const pct = progressPercent(s)
            return (
              <div key={s.id} className="list-item migration-session-row">
                <div>
                  <strong>{MODE_LABEL[s.mode] || s.mode}</strong>
                  <p className="muted">
                    {STATUS_LABEL[s.status] || s.status}
                    {s.last_activity_at
                      ? ` · dernière activité ${new Date(s.last_activity_at).toLocaleString('fr-FR')}`
                      : ''}
                  </p>
                  {pct != null ? (
                    <div className="migration-progress-inline" aria-label={`Progression ${pct} %`}>
                      <div className="migration-progress-bar">
                        <span style={{ width: `${pct}%` }} />
                      </div>
                      <span className="muted">{pct} %</span>
                    </div>
                  ) : null}
                </div>
                <div className="migration-session-actions">
                  {canResumeStatus(s.status) ? (
                    <button
                      type="button"
                      className="btn"
                      disabled={busyId === s.id}
                      onClick={() => void resume(s)}
                    >
                      Reprendre
                    </button>
                  ) : (
                    <Link className="btn secondary" to={`/migration/${s.id}`}>
                      Consulter
                    </Link>
                  )}
                  {canCancelStatus(s.status) ? (
                    <button
                      type="button"
                      className="btn secondary"
                      disabled={busyId === s.id}
                      onClick={() => void cancel(s)}
                    >
                      Annuler
                    </button>
                  ) : null}
                </div>
              </div>
            )
          })}
        </div>
      ) : null}
    </>
  )
}
