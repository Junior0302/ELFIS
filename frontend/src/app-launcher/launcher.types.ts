/**
 * App Launcher Premium V1 — types
 */

import type { ProductId, ProductIdentity } from '../design-system/types'

export type LauncherProductState =
  | 'active'
  | 'available'
  | 'locked'
  | 'coming_soon'
  | 'beta'
  | 'unavailable'

export type ResolvedLauncherProduct = {
  product: ProductIdentity
  state: LauncherProductState
  canOpen: boolean
  route?: string
  label: string
  reason?: string
  /** True when this card is the real lastProduct continue target. */
  isLastUsed?: boolean
}

export type LauncherResolveContext = {
  currentProductId: ProductId | string
  /** Routes that exist in the SPA — only these are openable. */
  availableRoutes: ReadonlySet<string>
  /** Optional preview overrides (sandbox only) — never mutates registry. */
  previewOverrides?: Partial<
    Record<
      ProductId,
      {
        state?: LauncherProductState
        route?: string | null
        canOpen?: boolean
      }
    >
  >
  /** Future: subscription / permission flags per product. */
  entitlements?: Partial<Record<ProductId, boolean>>
  previewMode?: boolean
}

export type LauncherSections = {
  active: ResolvedLauncherProduct | null
  available: ResolvedLauncherProduct[]
  comingSoonFeatured: ResolvedLauncherProduct[]
  comingSoonGrouped: ResolvedLauncherProduct[]
  locked: ResolvedLauncherProduct[]
}

/**
 * Fallback featured coming-soon IDs when registry `featuredInLauncher` is unset.
 * AnalyticsPilot is Home-only (not in Product Registry) — intentionally absent.
 */
export const LAUNCHER_FEATURED_COMING_SOON: readonly ProductId[] = [
  'docpilot',
  'hrpilot',
  'supportpilot',
  'salespilot',
]

export type AppLauncherViewport = 'desktop' | 'mobile'

export type AppLauncherMode = 'production' | 'sandbox_preview'

export type LauncherFooterLink = {
  id: string
  label: string
  to: string
}
