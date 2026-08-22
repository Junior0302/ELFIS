import { useEffect, useRef, type ReactNode, type RefObject } from 'react'
import type { ProductId } from '../design-system'
import { cx } from '../design-system'
import NotificationBell from '../components/notifications/NotificationBell'
import type { ProductShellChromeOptions } from './productShellConfig'
import { DEFAULT_SHELL_CHROME } from './productShellConfig'
import { OrganizationSwitcher } from './OrganizationSwitcher'
import { PlatformBrandLockup } from './PlatformBrandLockup'
import { PlatformLauncher } from './PlatformLauncher'
import { PlatformSearch } from './PlatformSearch'
import { ProductIndicator } from './ProductIndicator'
import { UserMenu } from './UserMenu'
import { ELFIS_GLOBAL_NAV_ID } from './global-nav/GlobalNavigationDrawer'
import { notifyProductShellViewportResize } from './productSidebarCollapse'

type PlatformTopBarProps = {
  productId: ProductId
  onMenuClick?: () => void
  menuOpen?: boolean
  menuButtonRef?: RefObject<HTMLButtonElement | null>
  className?: string
  chrome?: Partial<ProductShellChromeOptions>
}

/**
 * Hiérarchie topbar :
 * [menu global ELFIS][Apps][ELFIS Core → /home][produit][search][org][notifs][profil]
 * (nav produit mobile : contrôle distinct hors topbar — voir PlatformShell)
 */
export function PlatformTopBar({
  productId,
  onMenuClick,
  menuOpen,
  menuButtonRef,
  className,
  chrome: chromeOverrides,
}: PlatformTopBarProps) {
  const chrome = { ...DEFAULT_SHELL_CHROME, ...chromeOverrides }
  const menuLabel = menuOpen ? 'Fermer le menu ELFIS' : 'Ouvrir le menu ELFIS'

  return (
    <header className={cx('ps-topbar', className)}>
      <div className="ps-topbar__left">
        {onMenuClick ? (
          <button
            ref={menuButtonRef}
            type="button"
            className="ps-icon-btn ps-topbar__menu"
            aria-label={menuLabel}
            aria-expanded={Boolean(menuOpen)}
            aria-controls={ELFIS_GLOBAL_NAV_ID}
            onClick={onMenuClick}
          >
            <span className="ps-burger" aria-hidden>
              <span />
              <span />
              <span />
            </span>
          </button>
        ) : null}
        {chrome.showLauncher ? <PlatformLauncher /> : null}
        <PlatformBrandLockup />
        {chrome.showProductIndicator ? <ProductIndicator productId={productId} /> : null}
      </div>
      <div className="ps-topbar__center">
        {chrome.showSearch ? <PlatformSearch /> : null}
      </div>
      <div className="ps-topbar__right">
        {chrome.showOrganizationSwitcher ? <OrganizationSwitcher /> : null}
        {chrome.showNotifications ? (
          <div className="ps-topbar__notif">
            <NotificationBell />
          </div>
        ) : null}
        <UserMenu />
      </div>
    </header>
  )
}

type PlatformSidebarProps = {
  children: ReactNode
  className?: string
  title?: string
}

export function PlatformSidebar({ children, className, title }: PlatformSidebarProps) {
  return (
    <aside className={cx('ps-sidebar', className)} aria-label={title ?? 'Navigation produit'}>
      {title ? <p className="ps-sidebar__title">{title}</p> : null}
      <div className="ps-sidebar__body">{children}</div>
    </aside>
  )
}

type WorkspaceViewportProps = {
  children: ReactNode
  className?: string
}

export function WorkspaceViewport({ children, className }: WorkspaceViewportProps) {
  const ref = useRef<HTMLElement>(null)

  useEffect(() => {
    const el = ref.current
    if (!el || typeof ResizeObserver === 'undefined') return
    const observer = new ResizeObserver(() => {
      notifyProductShellViewportResize()
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  return (
    <main ref={ref} className={cx('ps-viewport', className)} id="platform-workspace">
      {children}
    </main>
  )
}
