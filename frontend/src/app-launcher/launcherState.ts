/**
 * Pure launcher state resolution — no React, no fetch.
 */

import {
  getComingSoonProducts,
  getLauncherProducts,
  getProductById,
  getProductCategory,
  isKnownProductId,
  isProductAvailable,
} from '../design-system/products/helpers'
import { PRODUCT_REGISTRY } from '../design-system/products/registry'
import type { ProductId, ProductIdentity } from '../design-system/types'
import { getProductEntryRoute } from './productEntryRoutes'
import {
  LAUNCHER_FEATURED_COMING_SOON,
  type LauncherResolveContext,
  type LauncherSections,
  type ResolvedLauncherProduct,
  type LauncherProductState,
} from './launcher.types'

const STATE_LABELS: Record<LauncherProductState, string> = {
  active: 'Application active',
  available: 'Ouvrir',
  locked: 'Non inclus dans votre abonnement',
  coming_soon: 'Bientôt disponible',
  beta: 'Bêta',
  unavailable: 'Indisponible',
}

export function resolveLauncherProductState(
  product: ProductIdentity,
  context: LauncherResolveContext,
): ResolvedLauncherProduct {
  const override = context.previewOverrides?.[product.id]
  if (override?.state) {
    const route =
      override.route === null
        ? undefined
        : (override.route ?? getProductEntryRoute(product.id) ?? undefined)
    const canOpen =
      override.canOpen ??
      (override.state === 'available' || override.state === 'beta' || override.state === 'active')
    return {
      product,
      state: override.state,
      canOpen: Boolean(canOpen && route && context.availableRoutes.has(route)),
      route: canOpen ? route : undefined,
      label: STATE_LABELS[override.state],
      reason: override.state === 'coming_soon' ? 'Cette application est en préparation.' : undefined,
    }
  }

  if (product.status === 'archived' || product.status === 'internal') {
    return {
      product,
      state: 'unavailable',
      canOpen: false,
      label: STATE_LABELS.unavailable,
      reason: 'Produit non exposé',
    }
  }

  if (product.id === context.currentProductId) {
    const route = getProductEntryRoute(product.id) ?? undefined
    return {
      product,
      state: 'active',
      canOpen: false,
      route,
      label: STATE_LABELS.active,
    }
  }

  if (product.status === 'coming_soon') {
    return {
      product,
      state: 'coming_soon',
      canOpen: false,
      label: STATE_LABELS.coming_soon,
      reason: 'Cette application est en préparation.',
    }
  }

  const entry = getProductEntryRoute(product.id)
  const hasRoute = Boolean(entry && context.availableRoutes.has(entry))
  const registryAvailable = isProductAvailable(product.id)

  if (context.entitlements && product.id in context.entitlements && !context.entitlements[product.id]) {
    return {
      product,
      state: 'locked',
      canOpen: false,
      route: entry ?? undefined,
      label: STATE_LABELS.locked,
      reason: 'Disponible avec une autre offre',
    }
  }

  if (registryAvailable && hasRoute && product.status === 'beta') {
    return {
      product,
      state: 'beta',
      canOpen: true,
      route: entry!,
      label: STATE_LABELS.beta,
    }
  }

  if (registryAvailable && hasRoute) {
    return {
      product,
      state: 'available',
      canOpen: true,
      route: entry!,
      label: STATE_LABELS.available,
    }
  }

  if (registryAvailable && !hasRoute) {
    return {
      product,
      state: 'unavailable',
      canOpen: false,
      label: STATE_LABELS.unavailable,
      reason: 'Aucune route d’application disponible',
    }
  }

  return {
    product,
    state: 'unavailable',
    canOpen: false,
    label: STATE_LABELS.unavailable,
  }
}

/**
 * Build launcher sections for UI.
 * Platform (elfis-core) is not listed as an openable card — header only.
 * Active product appears once. Featured coming soon = Sales + Doc.
 */
export function buildLauncherSections(context: LauncherResolveContext): LauncherSections {
  const currentId = isKnownProductId(context.currentProductId)
    ? context.currentProductId
    : 'comptapilot'

  let active: ResolvedLauncherProduct | null = null
  try {
    active = resolveLauncherProductState(getProductById(currentId), {
      ...context,
      currentProductId: currentId,
    })
    if (active.state !== 'active') {
      active = {
        ...active,
        state: 'active',
        canOpen: false,
        label: STATE_LABELS.active,
      }
    }
  } catch {
    active = null
  }

  const available: ResolvedLauncherProduct[] = []
  const locked: ResolvedLauncherProduct[] = []

  for (const product of getLauncherProducts()) {
    if (product.id === 'elfis-core') continue
    if (product.id === currentId) continue
    const resolved = resolveLauncherProductState(product, context)
    if (resolved.state === 'available' || resolved.state === 'beta') {
      available.push(resolved)
    } else if (resolved.state === 'locked') {
      locked.push(resolved)
    }
  }

  /* Preview may inject available products not in getLauncherProducts */
  if (context.previewMode && context.previewOverrides) {
    for (const [id, ov] of Object.entries(context.previewOverrides)) {
      if (!ov?.state || (ov.state !== 'available' && ov.state !== 'beta' && ov.state !== 'locked')) continue
      if (id === currentId || id === 'elfis-core') continue
      if (available.some((a) => a.product.id === id) || locked.some((a) => a.product.id === id)) continue
      try {
        const resolved = resolveLauncherProductState(getProductById(id as ProductId), context)
        if (resolved.state === 'available' || resolved.state === 'beta') available.push(resolved)
        if (resolved.state === 'locked') locked.push(resolved)
      } catch {
        /* ignore */
      }
    }
  }

  const comingSoonFeatured: ResolvedLauncherProduct[] = []
  const comingSoonGrouped: ResolvedLauncherProduct[] = []

  for (const product of getComingSoonProducts()) {
    if (product.id === currentId) continue
    const resolved = resolveLauncherProductState(product, context)
    if (resolved.state !== 'coming_soon' && !(context.previewOverrides?.[product.id])) {
      /* preview may change state — skip coming soon lists if overridden to available */
      if (resolved.state === 'available' || resolved.state === 'beta' || resolved.state === 'locked') continue
    }
    if (resolved.state !== 'coming_soon') continue
    const featured =
      product.featuredInLauncher === true ||
      (product.featuredInLauncher !== false && LAUNCHER_FEATURED_COMING_SOON.includes(product.id))
    if (featured) {
      comingSoonFeatured.push(resolved)
    } else {
      comingSoonGrouped.push(resolved)
    }
  }

  return { active, available, comingSoonFeatured, comingSoonGrouped, locked }
}

export function getCategoryLabel(product: ProductIdentity): string {
  try {
    return getProductCategory(product.id).label
  } catch {
    return product.category
  }
}

/** Safe list of all registry products for tests / debug. */
export function listRegistryForLauncher(): readonly ProductIdentity[] {
  return PRODUCT_REGISTRY
}

export { STATE_LABELS }
