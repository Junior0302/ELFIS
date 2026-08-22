import { useEffect, useState, type CSSProperties } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import { formatNotificationDate, type AppNotification } from '../notificationFormat'
import { ElfisEmptyState } from '../unified-platform'
import { relativeCheckLabel } from './homeSignals'
import { PlatformHomeSection } from './PlatformHomeSection'

export type TimelineEntry = {
  id: string
  title: string
  detail: string
  at: string
  source: 'notification' | 'session' | 'sync'
  href?: string
  spaceLabel?: string
  accent?: string
}

type GlobalTimelineProps = {
  lastProductLabel?: string | null
  lastProductAt?: string | null
  lastProductTo?: string | null
  lastProductAccent?: string | null
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
    spaceLabel: 'Plateforme',
  }
}

export function GlobalTimeline({
  lastProductLabel,
  lastProductAt,
  lastProductTo,
  lastProductAccent,
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
      spaceLabel: lastProductLabel,
      accent: lastProductAccent ?? undefined,
    })
  }
  if (syncTickAt) {
    extras.push({
      id: 'sync-tick',
      title: 'Synchronisation',
      detail: syncMode ? `Pulse ${syncMode}` : 'Pulse notifications',
      at: relativeCheckLabel(syncTickAt),
      source: 'sync',
      spaceLabel: 'Plateforme',
    })
  }

  const items = [...notifs, ...extras].slice(0, 8)

  return (
    <PlatformHomeSection
      id="home-activity"
      title="Activité récente"
      description="Notifications, session et synchronisation — sources réelles."
      level={4}
      className={`cockpit-timeline ph-activity ${embedded ? 'cockpit-timeline--embedded' : ''}`.trim()}
    >
      <div data-cockpit-timeline="v1">
        {!loaded ? (
          <p className="cockpit-timeline__loading">Chargement…</p>
        ) : items.length === 0 ? (
          <ElfisEmptyState
            title="Aucune activité récente"
            description="Dès qu’une notification, une session ou un pulse sync arrive, elle apparaîtra ici."
          />
        ) : (
          <ol className="cockpit-timeline__list ph-activity__list">
            {items.map((item) => (
              <li
                key={item.id}
                data-source={item.source}
                style={
                  item.accent
                    ? ({ '--ph-activity-accent': item.accent } as CSSProperties)
                    : undefined
                }
              >
                <span className="cockpit-timeline__dot" aria-hidden />
                <div>
                  <strong>{item.title}</strong>
                  <span>{item.detail}</span>
                  {item.spaceLabel ? (
                    <span className="ph-activity__space">{item.spaceLabel}</span>
                  ) : null}
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
      </div>
    </PlatformHomeSection>
  )
}
