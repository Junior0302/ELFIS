import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import {
  categoryLabel,
  formatNotificationDate,
  isSafeInternalActionUrl,
  severityLabel,
  type AppNotification,
} from '../notificationFormat'

export default function NotificationsPage() {
  const { token, orgId } = useAuth()
  const [items, setItems] = useState<AppNotification[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState<'all' | 'unread'>('all')
  const [category, setCategory] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    if (!token || !orgId) return
    setLoading(true)
    setError('')
    try {
      const data = await api.listNotifications(
        {
          page,
          page_size: 20,
          status: statusFilter === 'unread' ? 'unread' : undefined,
          category: category || undefined,
        },
        token,
        orgId,
      )
      setItems(data.notifications || [])
      setTotal(data.total || 0)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible de charger les notifications')
    } finally {
      setLoading(false)
    }
  }, [token, orgId, page, statusFilter, category])

  useEffect(() => {
    void load()
  }, [load])

  const markRead = async (id: string) => {
    if (!token || !orgId || busy) return
    setBusy(true)
    try {
      await api.markElfisNotificationRead(id, token, orgId)
      await load()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Action impossible')
    } finally {
      setBusy(false)
    }
  }

  const markAll = async () => {
    if (!token || !orgId || busy) return
    setBusy(true)
    try {
      await api.markAllElfisNotificationsRead(token, orgId)
      await load()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Action impossible')
    } finally {
      setBusy(false)
    }
  }

  const archive = async (id: string) => {
    if (!token || !orgId || busy) return
    setBusy(true)
    try {
      await api.archiveElfisNotification(id, token, orgId)
      await load()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Action impossible')
    } finally {
      setBusy(false)
    }
  }

  const pageCount = Math.max(1, Math.ceil(total / 20))

  return (
    <div className="page notifications-page">
      <header className="page-head">
        <div>
          <h2>Notifications</h2>
          <p className="muted">Centre d’alertes de votre organisation</p>
        </div>
        <div className="actions">
          <button className="btn secondary" type="button" onClick={() => void load()} disabled={loading || busy}>
            Actualiser
          </button>
          <button className="btn" type="button" onClick={() => void markAll()} disabled={busy}>
            Tout marquer comme lu
          </button>
        </div>
      </header>

      <div className="toolbar" style={{ gap: '0.75rem', flexWrap: 'wrap' }}>
        <div className="billing-tabs" role="tablist">
          <button
            type="button"
            className={`billing-tab ${statusFilter === 'all' ? 'active' : ''}`}
            onClick={() => {
              setPage(1)
              setStatusFilter('all')
            }}
          >
            Toutes
          </button>
          <button
            type="button"
            className={`billing-tab ${statusFilter === 'unread' ? 'active' : ''}`}
            onClick={() => {
              setPage(1)
              setStatusFilter('unread')
            }}
          >
            Non lues
          </button>
        </div>
        <label className="field" style={{ margin: 0, minWidth: 160 }}>
          <span className="muted">Catégorie</span>
          <select
            value={category}
            onChange={(e) => {
              setPage(1)
              setCategory(e.target.value)
            }}
          >
            <option value="">Toutes</option>
            <option value="email">E-mail</option>
            <option value="vault">Vault</option>
            <option value="billing">Facturation</option>
            <option value="subscription">Abonnement</option>
            <option value="system">Système</option>
            <option value="security">Sécurité</option>
          </select>
        </label>
      </div>

      {error && <p className="form-error">{error}</p>}
      {loading && <p className="loading">Chargement…</p>}

      {!loading && items.length === 0 && (
        <div className="panel empty">
          <p>Aucune notification pour le moment.</p>
        </div>
      )}

      {!loading && items.length > 0 && (
        <div className="list">
          {items.map((item) => (
            <div key={item.notification_id} className="list-item notif-list-item">
              <div>
                <strong>{item.title}</strong>
                <span>{item.message}</span>
                <span className="muted">
                  {categoryLabel(item.category)} · {severityLabel(item.severity)} ·{' '}
                  {formatNotificationDate(item.created_at)}
                  {item.status === 'unread' ? ' · Non lue' : ''}
                </span>
              </div>
              <div className="actions" style={{ flexWrap: 'wrap' }}>
                {isSafeInternalActionUrl(item.action_url) && (
                  <Link className="btn secondary" to={item.action_url!}>
                    {item.action_label || 'Ouvrir'}
                  </Link>
                )}
                {item.status === 'unread' && (
                  <button className="btn secondary" type="button" disabled={busy} onClick={() => void markRead(item.notification_id)}>
                    Marquer lue
                  </button>
                )}
                <button className="btn secondary" type="button" disabled={busy} onClick={() => void archive(item.notification_id)}>
                  Archiver
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {pageCount > 1 && (
        <div className="actions" style={{ marginTop: '1rem' }}>
          <button className="btn secondary" type="button" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            Précédent
          </button>
          <span className="muted">
            Page {page} / {pageCount}
          </span>
          <button
            className="btn secondary"
            type="button"
            disabled={page >= pageCount}
            onClick={() => setPage((p) => p + 1)}
          >
            Suivant
          </button>
        </div>
      )}
    </div>
  )
}
