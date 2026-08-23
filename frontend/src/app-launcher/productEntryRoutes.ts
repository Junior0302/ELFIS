/**
 * Product entry routes — real SPA entry points only.
 * websitePath marketing is never used as an app route.
 */

import type { ProductId } from '../design-system/types'

/**
 * null = no real application shell yet — product cannot be opened.
 */
export const PRODUCT_ENTRY_ROUTES: Readonly<Record<ProductId, string | null>> = {
  'elfis-core': null,
  comptapilot: '/dashboard',
  salespilot: '/sales',
  docpilot: null,
  hrpilot: null,
  legalpilot: null,
  inventorypilot: null,
  marketingpilot: null,
  projectpilot: null,
  supportpilot: null,
}

export function getProductEntryRoute(productId: ProductId): string | null {
  return PRODUCT_ENTRY_ROUTES[productId] ?? null
}

/**
 * Routes known to exist in the current SPA shell.
 * Inclut entrées produits + coffre plateforme (espace Documents).
 */
export function getKnownSpaRoutes(): ReadonlySet<string> {
  const routes = new Set(
    Object.values(PRODUCT_ENTRY_ROUTES).filter((r): r is string => typeof r === 'string' && r.length > 0),
  )
  routes.add('/platform/documents')
  routes.add('/platform/banking')
  routes.add('/platform/help')
  routes.add('/platform/search')
  routes.add('/platform/relations')
  return routes
}
