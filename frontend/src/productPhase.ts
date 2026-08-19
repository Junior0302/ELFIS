import type { SubscriptionInfo } from './api'
import { hasFinancialEntitlement } from './subscription'

/**
 * Phases produit — Sprint 2.3.
 * `company_setup` sera ajouté plus tard.
 */
export type ProductPhase = 'loading' | 'no_entitlement' | 'entitled'

/** Routes accessibles sans entitlement (PublicLayout). */
export const PUBLIC_PRODUCT_PATHS = ['/welcome', '/abonnement', '/compte'] as const

export function resolveProductPhase(
  subscription: SubscriptionInfo | null | undefined,
  opts?: { isPlatformAdmin?: boolean; subscriptionLoading?: boolean },
): ProductPhase {
  // Initial gate only — never unmount the entitled workspace during a background
  // subscription refresh (e.g. window focus). That was wiping open overlays / forms.
  if (opts?.subscriptionLoading && subscription == null && !opts?.isPlatformAdmin) {
    return 'loading'
  }
  if (hasFinancialEntitlement(subscription, opts)) return 'entitled'
  return 'no_entitlement'
}

export function normalizeProductPath(pathname: string): string {
  const trimmed = pathname.replace(/\/+$/, '')
  return trimmed || '/'
}

export function isPublicProductPath(pathname: string): boolean {
  const path = normalizeProductPath(pathname)
  return PUBLIC_PRODUCT_PATHS.some((p) => path === p || path.startsWith(`${p}/`))
}

export function isWelcomePath(pathname: string): boolean {
  const path = normalizeProductPath(pathname)
  return path === '/welcome' || path.startsWith('/welcome/')
}
