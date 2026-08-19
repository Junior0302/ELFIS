/**
 * Source unique — préférence + signaux resize pour le rail produit (ComptaPilot).
 * Largeurs layout : variables CSS --product-sidebar-* (voir platform-shell.css).
 */
export const PRODUCT_SIDEBAR_COLLAPSED_STORAGE_KEY = 'elfis.productSidebarCollapsed'
/** Legacy ComptaPilot — lu en migration, réécrit pour compat. */
export const LEGACY_COMPTA_SIDEBAR_COLLAPSED_KEY = 'cp_sidebar_collapsed'

export const PRODUCT_SIDEBAR_EXPANDED_WIDTH_PX = 240
export const PRODUCT_SIDEBAR_COLLAPSED_WIDTH_PX = 56
export const PRODUCT_SIDEBAR_TRANSITION_MS = 180

export const PRODUCT_SHELL_VIEWPORT_RESIZE_EVENT = 'elfis:product-shell-viewport-resize'

export const COMPTA_PRODUCT_NAV_ID = 'compta-product-nav'

export function readProductSidebarCollapsedPreference(): boolean {
  try {
    const next = localStorage.getItem(PRODUCT_SIDEBAR_COLLAPSED_STORAGE_KEY)
    if (next === '1' || next === 'true') return true
    if (next === '0' || next === 'false') return false
    return localStorage.getItem(LEGACY_COMPTA_SIDEBAR_COLLAPSED_KEY) === '1'
  } catch {
    return false
  }
}

export function writeProductSidebarCollapsedPreference(collapsed: boolean): void {
  const value = collapsed ? '1' : '0'
  try {
    localStorage.setItem(PRODUCT_SIDEBAR_COLLAPSED_STORAGE_KEY, value)
    localStorage.setItem(LEGACY_COMPTA_SIDEBAR_COLLAPSED_KEY, value)
  } catch {
    /* quota / private mode */
  }
}

export type NotifyViewportResizeOptions = {
  /** Miroir `window` resize — utile après collapse (pas depuis ResizeObserver). */
  mirrorWindowResize?: boolean
}

export function notifyProductShellViewportResize(
  options: NotifyViewportResizeOptions = {},
): void {
  if (typeof window === 'undefined') return
  window.dispatchEvent(new CustomEvent(PRODUCT_SHELL_VIEWPORT_RESIZE_EVENT))
  if (options.mirrorWindowResize) {
    window.dispatchEvent(new Event('resize'))
  }
}
