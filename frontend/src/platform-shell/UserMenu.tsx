import { useEffect, useId, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import { cx } from '../design-system'
import { closeAllOverlays } from '../design-system/overlays/manager/overlayLifecycle'
import { userInitials } from '../components/layouts/layoutUtils'
import { ELFIS_CLOSE_CHROME_MENUS } from './global-nav/chromeMenus'

type UserMenuProps = {
  className?: string
}

export function UserMenu({ className }: UserMenuProps) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const panelId = useId()
  const name = user ? `${user.first_name} ${user.last_name}`.trim() || user.email : 'Utilisateur'
  const initials = userInitials(user?.first_name, user?.last_name)

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

  useEffect(() => {
    const onCloseChrome = () => setOpen(false)
    window.addEventListener(ELFIS_CLOSE_CHROME_MENUS, onCloseChrome)
    return () => window.removeEventListener(ELFIS_CLOSE_CHROME_MENUS, onCloseChrome)
  }, [])

  const close = () => setOpen(false)

  return (
    <div className={cx('ps-user', className)} ref={rootRef}>
      <button
        type="button"
        className="ps-user__trigger"
        aria-expanded={open}
        aria-controls={panelId}
        aria-haspopup="menu"
        onClick={() => {
          setOpen((v) => {
            const next = !v
            if (next) {
              closeAllOverlays('programmatic')
            }
            return next
          })
        }}
      >
        <span className="ps-user__avatar" aria-hidden>
          {initials}
        </span>
        <span className="ps-user__meta">
          <strong>{name}</strong>
          <span>{user?.email}</span>
        </span>
      </button>
      {open ? (
        <div className="ps-user__panel" id={panelId} role="menu" aria-label="Menu utilisateur">
          <Link
            role="menuitem"
            to="/home"
            className="ps-user__item"
            onClick={() => {
              close()
              closeAllOverlays('route_change')
            }}
          >
            ELFIS Home
          </Link>
          <Link role="menuitem" to="/compte" className="ps-user__item" onClick={close}>
            Mon compte
          </Link>
          <Link role="menuitem" to="/platform/organization" className="ps-user__item" onClick={close}>
            Organisation
          </Link>
          <Link
            role="menuitem"
            to="/platform/settings"
            className="ps-user__item"
            onClick={close}
          >
            Paramètres ELFIS
          </Link>
          <Link role="menuitem" to="/compte" className="ps-user__item" onClick={close}>
            Préférences
          </Link>
          <button
            type="button"
            role="menuitem"
            className="ps-user__item ps-user__item--danger"
            onClick={() => {
              close()
              logout()
              navigate('/login', { replace: true })
            }}
          >
            Déconnexion
          </button>
        </div>
      ) : null}
    </div>
  )
}
