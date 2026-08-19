/**
 * Cross-cutting lifecycle bridge — auth / org / product / route
 * without coupling OverlayProvider to AuthProvider.
 */

import type { OverlayCloseReason } from './types'

type CloseAllFn = (reason: OverlayCloseReason) => void

let boundCloseAll: CloseAllFn | null = null

/** Called by OverlayProvider on mount. */
export function bindOverlayCloseAll(fn: CloseAllFn | null): void {
  boundCloseAll = fn
}

/**
 * Imperative helper for auth / org / future App Launcher.
 * Safe no-op if no OverlayProvider is mounted.
 */
export function closeAllOverlays(reason: OverlayCloseReason): void {
  boundCloseAll?.(reason)
}

/** Documented integration points — do not invent new systems. */
export const OVERLAY_LIFECYCLE_HOOKS = {
  logout: 'logout' as const,
  organizationChange: 'organization_change' as const,
  productChange: 'product_change' as const,
  routeChange: 'route_change' as const,
}
