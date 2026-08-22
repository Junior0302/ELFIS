import { useCallback, useRef, useState, type ReactNode } from 'react'
import type { ProductId } from '../design-system'
import { cx } from '../design-system'
import { closeAllOverlays } from '../design-system/overlays/manager/overlayLifecycle'
import type { ProductShellChromeOptions } from './productShellConfig'
import { DEFAULT_SHELL_CHROME } from './productShellConfig'
import { PlatformSidebar, PlatformTopBar, WorkspaceViewport } from './PlatformTopBar'
import { GlobalNavigationDrawer } from './global-nav/GlobalNavigationDrawer'
import { closeChromeMenus } from './global-nav/chromeMenus'
import './platform-shell.css'

export type PlatformShellSidebarApi = {
  closeMobileNav: () => void
  openMobileNav: () => void
}

export type PlatformShellProps = {
  productId: ProductId
  sidebar?: ReactNode | ((api: PlatformShellSidebarApi) => ReactNode)
  sidebarTitle?: string
  sidebarClassName?: string
  /** Rail produit réduit — sync grid via --product-sidebar-current-width */
  sidebarCollapsed?: boolean
  children: ReactNode
  className?: string
  chrome?: Partial<ProductShellChromeOptions>
  /** Espace métier (finance / commercial / documents) — tokens --workspace-*. */
  dataWorkspace?: string
}

/**
 * Shell officiel ELFIS Core — aucune branche produit ici.
 * Hamburger topbar → menu global ELFIS (pas la sidebar produit).
 */
export function PlatformShell({
  productId,
  sidebar,
  sidebarTitle,
  sidebarClassName,
  sidebarCollapsed = false,
  children,
  className,
  chrome: chromeOverrides,
  dataWorkspace,
}: PlatformShellProps) {
  const chrome: ProductShellChromeOptions = { ...DEFAULT_SHELL_CHROME, ...chromeOverrides }
  const [globalNavOpen, setGlobalNavOpen] = useState(false)
  const [mobileProductNavOpen, setMobileProductNavOpen] = useState(false)
  const menuButtonRef = useRef<HTMLButtonElement>(null)
  const hasSidebar = Boolean(sidebar)
  const closeMobileNav = useCallback(() => setMobileProductNavOpen(false), [])
  const openMobileNav = useCallback(() => {
    setGlobalNavOpen(false)
    setMobileProductNavOpen(true)
  }, [])

  const sidebarContent =
    typeof sidebar === 'function' ? sidebar({ closeMobileNav, openMobileNav }) : sidebar

  const onGlobalMenuClick = useCallback(() => {
    if (globalNavOpen) {
      setGlobalNavOpen(false)
      return
    }
    closeAllOverlays('programmatic')
    closeChromeMenus()
    setMobileProductNavOpen(false)
    setGlobalNavOpen(true)
  }, [globalNavOpen])

  return (
    <div
      className={cx(
        'ps-shell',
        hasSidebar && 'ps-shell--with-sidebar',
        hasSidebar && sidebarCollapsed && 'ps-shell--sidebar-collapsed',
        className,
      )}
      data-platform-shell="v1"
      data-product={productId}
      data-sidebar-collapsed={hasSidebar && sidebarCollapsed ? 'true' : 'false'}
      data-workspace={dataWorkspace}
    >
      <PlatformTopBar
        productId={productId}
        chrome={chrome}
        menuOpen={globalNavOpen}
        onMenuClick={onGlobalMenuClick}
        menuButtonRef={menuButtonRef}
      />
      <div className="ps-shell__body">
        {hasSidebar ? (
          <PlatformSidebar
            className={cx(mobileProductNavOpen && 'ps-sidebar--mobile-open', sidebarClassName)}
            title={sidebarTitle}
          >
            {sidebarContent}
          </PlatformSidebar>
        ) : null}
        {hasSidebar && mobileProductNavOpen ? (
          <button
            type="button"
            className="ps-shell__scrim"
            aria-label="Fermer la navigation produit"
            onClick={closeMobileNav}
          />
        ) : null}
        <WorkspaceViewport>
          {hasSidebar && !mobileProductNavOpen ? (
            <button
              type="button"
              className="ps-shell__open-product-nav"
              aria-label="Ouvrir la navigation produit"
              onClick={openMobileNav}
            >
              <span className="ps-shell__open-product-nav-glyph" aria-hidden>
                ▤
              </span>
              <span className="ps-shell__open-product-nav-label">Navigation</span>
            </button>
          ) : null}
          {children}
        </WorkspaceViewport>
      </div>

      <GlobalNavigationDrawer
        open={globalNavOpen}
        onOpenChange={setGlobalNavOpen}
        returnFocusRef={menuButtonRef}
      />
    </div>
  )
}

export { PlatformTopBar, PlatformSidebar, WorkspaceViewport } from './PlatformTopBar'
export { PlatformLauncher } from './PlatformLauncher'
export { PlatformSearch } from './PlatformSearch'
export { NotificationCenter } from './NotificationCenter'
export { OrganizationSwitcher } from './OrganizationSwitcher'
export { UserMenu } from './UserMenu'
export { ProductIndicator } from './ProductIndicator'
