import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api'
import { useAuth } from '../../auth'
import {
  formatNotificationDate,
  formatUnreadBadge,
  isSafeInternalActionUrl,
  type AppNotification,
} from '../../notificationFormat'
import { useSync } from '../../sync/SyncProvider'
import { ELFIS_CLOSE_CHROME_MENUS } from '../../platform-shell/global-nav/chromeMenus'

type Props = {
  compact?: boolean
}

export default function NotificationBell({ compact }: Props) {
  const { token, orgId } = useAuth()
  const { unreadNotifications, refresh } = useSync()
  const [open, setOpen] = useState(false)
  const [items, setItems] = useState<AppNotification[]>([])
  const [loading, setLoading] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)

  const count = unreadNotifications

  const refreshPreview = async () => {
    if (!token || !orgId) return
    setLoading(true)
    try {
      const data = await api.listNotifications(
        { page: 1, page_size: 5, status: 'unread' },
        token,
        orgId,
      )
      setItems(data.notifications || [])
      await refresh('notifications')
    } catch {
      setItems([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!open) return
    void refreshPreview()
    const onDoc = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [open])

  useEffect(() => {
    const onCloseChrome = () => setOpen(false)
    window.addEventListener(ELFIS_CLOSE_CHROME_MENUS, onCloseChrome)
    return () => window.removeEventListener(ELFIS_CLOSE_CHROME_MENUS, onCloseChrome)
  }, [])

  const badge = formatUnreadBadge(count)

  return (
    <div className={`notif-bell ${compact ? 'compact' : ''}`} ref={rootRef}>
      <button
        type="button"
        className="notif-bell-btn"
        aria-label="Notifications"
        aria-expanded={open}
        onClick={() => {
          setOpen((v) => {
            const next = !v
            if (next) {
              window.dispatchEvent(new CustomEvent(ELFIS_CLOSE_CHROME_MENUS))
            }
            return next
          })
        }}
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
          <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
          <path d="M10 21a2 2 0 0 0 4 0" />
        </svg>
        {badge ? <span className="notif-bell-badge">{badge}</span> : null}
      </button>
      {open && (
        <div className="notif-bell-menu" role="menu">
          <header className="notif-bell-head">
            <strong>Notifications</strong>
            <Link to="/notifications" onClick={() => setOpen(false)}>
              Voir toutes
            </Link>
          </header>
          {loading && <p className="muted">Chargement…</p>}
          {!loading && items.length === 0 && (
            <p className="muted">Aucune notification non lue.</p>
          )}
          {!loading &&
            items.map((item) => (
              <div key={item.notification_id} className="notif-bell-item">
                <strong>{item.title}</strong>
                <span>{item.message}</span>
                <em>{formatNotificationDate(item.created_at)}</em>
                {isSafeInternalActionUrl(item.action_url) && (
                  <Link to={item.action_url!} onClick={() => setOpen(false)}>
                    {item.action_label || 'Ouvrir'}
                  </Link>
                )}
              </div>
            ))}
        </div>
      )}
    </div>
  )
}
