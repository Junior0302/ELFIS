import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import { formatNotificationDate, type AppNotification } from '../notificationFormat'
import { ElfisEmptyState } from '../unified-platform'
import { relativeCheckLabel } from './homeSignals'

export type TimelineEntry = {
  id: string
  title: string
  detail: string
  at: string
  source: 'notification' | 'session' | 'sync'
  href?: string
}

type GlobalTimelineProps = {
  lastProductLabel?: string | null
  lastProductAt?: string | null
  lastProductTo?: string | null
  syncTickAt?: string
  syncMode?: string
  embedded?: boolean
}

function mapNotif(n: AppNotification): TimelineEntry {
  return {
    id: `n-${n.notification_id}`,
    title: n.title || 'Notification',
    detail: n.message || n.category || 'Notification plateforme',
    at: formatNotificationDate(n.created_at) || '—',
    source: 'notification',
    href: '/notifications',
  }
}

export function GlobalTimeline({
  lastProductLabel,
  lastProductAt,
  lastProductTo,
  syncTickAt,
  syncMode,
  embedded = false,
}: GlobalTimelineProps) {
  const { token, orgId } = useAuth()
  const [notifs, setNotifs] = useState<TimelineEntry[]>([])
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    let cancelled = false
    if (!token || orgId == null) {
      setNotifs([])
      setLoaded(true)
      return
    }
    void (async () => {
      try {
        const data = await api.listNotifications({ page: 1, page_size: 8 }, token, orgId)
        if (cancelled) return
        setNotifs((data.notifications || []).map(mapNotif))
      } catch {
        if (cancelled) return
        setNotifs([])
      } finally {
        if (!cancelled) setLoaded(true)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [token, orgId])

  const extras: TimelineEntry[] = []
  if (lastProductLabel && lastProductAt) {
    extras.push({
      id: 'session-last',
      title: 'Session reprise',
      detail: lastProductLabel,
      at: relativeCheckLabel(lastProductAt),
      source: 'session',
      href: lastProductTo ?? undefined,
    })
  }
  if (syncTickAt) {
    extras.push({
      id: 'sync-tick',
      title: 'Synchronisation',
      detail: syncMode ? `Pulse ${syncMode}` : 'Pulse notifications',
      at: relativeCheckLabel(syncTickAt),
      source: 'sync',
    })
  }

  const items = [...notifs, ...extras].slice(0, 8)

  return (
    <section
      className={`cockpit-timeline ${embedded ? 'cockpit-timeline--embedded' : ''}`.trim()}
      id="home-activity"
      aria-labelledby="home-timeline-title"
      data-cockpit-timeline="v1"
    >
      <div className="elfis-home__section-head elfis-home__section-head--compact">
        <h2 id="home-timeline-title">Timeline globale</h2>
        <p>Sources réelles (notifications, session, sync).</p>
      </div>
      {!loaded ? (
        <p className="cockpit-timeline__loading">Chargement…</p>
      ) : items.length === 0 ? (
        <ElfisEmptyState
          title="Aucune activité récente"
          description="Dès qu’une notification, une session ou un pulse sync arrive, elle apparaîtra ici."
        />
      ) : (
        <ol className="cockpit-timeline__list">
          {items.map((item) => (
            <li key={item.id} data-source={item.source}>
              <span className="cockpit-timeline__dot" aria-hidden />
              <div>
                <strong>{item.title}</strong>
                <span>{item.detail}</span>
                <time>{item.at}</time>
                {item.href ? (
                  <Link className="cockpit-timeline__link" to={item.href}>
                    Ouvrir
                  </Link>
                ) : null}
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}
