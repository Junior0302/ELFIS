import { useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../auth'
import {
  formatNotificationDate,
  type AppNotification,
} from '../notificationFormat'

type PanelItem = {
  id: string
  title: string
  body: string
  at: string
  product: string
  type: 'info' | 'success' | 'system' | 'security'
}

function mapReal(n: AppNotification): PanelItem {
  const severity = (n.severity || '').toLowerCase()
  const category = (n.category || '').toLowerCase()
  let type: PanelItem['type'] = 'info'
  if (severity === 'critical' || category.includes('security')) type = 'security'
  else if (severity === 'success' || category.includes('success')) type = 'success'
  else if (category.includes('system') || category.includes('billing')) type = 'system'

  return {
    id: n.notification_id,
    title: n.title || 'Notification',
    body: n.message || '',
    at: formatNotificationDate(n.created_at) || '—',
    product: n.category || 'ELFIS Core',
    type,
  }
}

function NotifIcon({ type }: { type: PanelItem['type'] }) {
  const label =
    type === 'success'
      ? 'Succès'
      : type === 'security'
        ? 'Sécurité'
        : type === 'system'
          ? 'Système'
          : 'Info'
  return (
    <span className={`home-notif__icon home-notif__icon--${type}`} aria-hidden title={label}>
      {type === 'success' ? '✓' : type === 'security' ? '⌂' : type === 'system' ? '⚙' : 'i'}
    </span>
  )
}

export function HomeNotificationsPanel() {
  const { token, orgId } = useAuth()
  const [items, setItems] = useState<PanelItem[] | null>(null)
  const [source, setSource] = useState<'live' | 'empty' | 'preview'>('empty')

  useEffect(() => {
    let cancelled = false
    if (!token || orgId == null) {
      setItems([])
      setSource('empty')
      return
    }
    void (async () => {
      try {
        const data = await api.listNotifications({ page: 1, page_size: 5 }, token, orgId)
        if (cancelled) return
        const list = (data.notifications || []).map(mapReal)
        if (list.length > 0) {
          setItems(list)
          setSource('live')
        } else {
          setItems([])
          setSource('empty')
        }
      } catch {
        if (cancelled) return
        /* Honêteté : pas de mock trompeur si l’API échoue. */
        setItems([])
        setSource('empty')
      }
    })()
    return () => {
      cancelled = true
    }
  }, [token, orgId])

  const list = items ?? []

  return (
    <section
      className="home-notifs"
      id="home-notifications"
      aria-labelledby="home-notifs-title"
    >
      <div className="elfis-home__section-head">
        <h2 id="home-notifs-title">Notifications</h2>
        {source === 'preview' ? <p className="elfis-home__mock-badge">Aperçu</p> : null}
        {source === 'live' ? <p className="elfis-home__mock-badge">Réelles</p> : null}
      </div>
      {list.length === 0 ? (
        <p className="home-notifs__empty">Aucune notification pour le moment.</p>
      ) : (
        <ul className="home-notif-center" aria-label="Centre de notifications">
          {list.map((n) => (
            <li key={n.id} className="home-notif">
              <NotifIcon type={n.type} />
              <div className="home-notif__body">
                <div className="home-notif__row">
                  <strong>{n.title}</strong>
                  <time>{n.at}</time>
                </div>
                <span className="home-notif__meta">
                  <span className="home-notif__product">{n.product}</span>
                </span>
                {n.body ? <span className="home-notif__text">{n.body}</span> : null}
              </div>
            </li>
          ))}
        </ul>
      )}
      {source === 'preview' ? (
        <p className="elfis-home__mock-hint">
          Aperçu — le centre topbar reste branché aux notifications réelles.
        </p>
      ) : null}
    </section>
  )
}
