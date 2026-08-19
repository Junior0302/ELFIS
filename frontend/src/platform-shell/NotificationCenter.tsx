import { useEffect, useId, useMemo, useRef, useState } from 'react'
import { cx } from '../design-system'

type NotifCategory = 'Plateforme' | 'ComptaPilot' | 'SalesPilot' | 'DocPilot'

type ShellNotification = {
  id: string
  category: NotifCategory
  title: string
  body: string
  read: boolean
  at: string
}

const SEED: ShellNotification[] = [
  {
    id: 'n1',
    category: 'Plateforme',
    title: 'Bienvenue sur ELFIS Core',
    body: 'Votre espace plateforme est prêt.',
    read: false,
    at: 'Il y a 2 min',
  },
  {
    id: 'n2',
    category: 'SalesPilot',
    title: 'Opportunité mise à jour',
    body: 'Acme — étape Proposition (mock).',
    read: false,
    at: 'Il y a 1 h',
  },
  {
    id: 'n3',
    category: 'ComptaPilot',
    title: 'Facture à valider',
    body: 'F-2026-0142 en attente (mock).',
    read: true,
    at: 'Hier',
  },
  {
    id: 'n4',
    category: 'DocPilot',
    title: 'Document partagé',
    body: 'Contrat.pdf disponible (mock).',
    read: true,
    at: 'Hier',
  },
]

type NotificationCenterProps = {
  compact?: boolean
  className?: string
}

/** Centre de notifications — UI + données mock (pas de backend ajouté). */
export function NotificationCenter({ compact, className }: NotificationCenterProps) {
  const [open, setOpen] = useState(false)
  const [filter, setFilter] = useState<NotifCategory | 'Tous'>('Tous')
  const [items, setItems] = useState(SEED)
  const rootRef = useRef<HTMLDivElement>(null)
  const panelId = useId()

  const unread = items.filter((i) => !i.read).length

  const visible = useMemo(
    () => (filter === 'Tous' ? items : items.filter((i) => i.category === filter)),
    [items, filter],
  )

  useEffect(() => {
    if (!open) return
    const onDoc = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    window.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDoc)
      window.removeEventListener('keydown', onKey)
    }
  }, [open])

  const markAllRead = () => setItems((prev) => prev.map((i) => ({ ...i, read: true })))
  const markRead = (id: string) =>
    setItems((prev) => prev.map((i) => (i.id === id ? { ...i, read: true } : i)))

  const filters: Array<NotifCategory | 'Tous'> = [
    'Tous',
    'Plateforme',
    'ComptaPilot',
    'SalesPilot',
    'DocPilot',
  ]

  return (
    <div className={cx('ps-notif', compact && 'ps-notif--compact', className)} ref={rootRef}>
      <button
        type="button"
        className="ps-icon-btn"
        aria-expanded={open}
        aria-controls={panelId}
        aria-label={unread ? `Notifications, ${unread} non lues` : 'Notifications'}
        onClick={() => setOpen((v) => !v)}
      >
        <span aria-hidden>🔔</span>
        {unread > 0 ? <span className="ps-notif__badge">{unread > 9 ? '9+' : unread}</span> : null}
      </button>

      {open ? (
        <div className="ps-notif__panel" id={panelId} role="dialog" aria-label="Centre de notifications">
          <header className="ps-notif__head">
            <h2>Notifications</h2>
            <button type="button" className="ps-link-btn" onClick={markAllRead}>
              Tout marquer lu
            </button>
          </header>
          <div className="ps-notif__filters" role="tablist" aria-label="Filtrer">
            {filters.map((f) => (
              <button
                key={f}
                type="button"
                role="tab"
                aria-selected={filter === f}
                className={cx('ps-notif__chip', filter === f && 'is-active')}
                onClick={() => setFilter(f)}
              >
                {f}
              </button>
            ))}
          </div>
          <ul className="ps-notif__list">
            {visible.length === 0 ? (
              <li className="ps-notif__empty">Aucune notification</li>
            ) : (
              visible.map((item) => (
                <li key={item.id} className={cx(!item.read && 'is-unread')}>
                  <button type="button" className="ps-notif__item" onClick={() => markRead(item.id)}>
                    <span className="ps-notif__cat">{item.category}</span>
                    <strong>{item.title}</strong>
                    <span className="ps-notif__body">{item.body}</span>
                    <time>{item.at}</time>
                  </button>
                </li>
              ))
            )}
          </ul>
          <p className="ps-notif__footnote">Données de démonstration — pas de backend ajouté.</p>
        </div>
      ) : null}
    </div>
  )
}
