/**
 * Unique source of truth — runtime product from the real URL path.
 * Layouts / launcher / sandbox must NOT write the global theme directly.
 */

import type { ProductId } from '../types'

export type RuntimeProductResolution = {
  productId: ProductId
  /** Persist to localStorage (business apps only). */
  persist: boolean
  /** Public platform surface (login, landing). */
  surface: 'platform' | 'workspace' | 'sandbox'
  reason: 'route_public' | 'route_comptapilot' | 'route_salespilot' | 'route_sandbox' | 'route_fallback'
}

const PUBLIC_EXACT = new Set(['/', '/login', '/register', '/forgot-password'])

const COMPTAPILOT_PREFIXES = [
  '/dashboard',
  '/welcome',
  '/work-queue',
  '/decisions',
  '/clients',
  '/fournisseurs',
  '/facturation',
  '/devis',
  '/documents',
  '/deposit',
  '/accounting',
  '/financial',
  '/finance',
  '/tva',
  '/cloture',
  '/copilote',
  '/intelligence',
  '/history',
  '/result',
  '/search',
  '/catalogue',
  '/activites',
  '/settings',
  '/reports',
  '/cockpit',
  '/enterprise-setup',
  '/onboarding',
  '/migration',
] as const

const PLATFORM_EXACT = new Set([
  '/organisation',
  '/compte',
  '/abonnement',
  '/modules',
  '/notifications',
])

/**
 * Resolves the active runtime product from pathname.
 * Priority: sandbox → sales → home/platform → public → comptapilot shell → fallback elfis-core.
 */
export function resolveRuntimeProductFromPath(pathname: string): RuntimeProductResolution {
  const path = normalizePath(pathname)

  if (path.startsWith('/dev/design-system')) {
    return {
      productId: 'comptapilot',
      persist: false,
      surface: 'sandbox',
      reason: 'route_sandbox',
    }
  }

  if (path === '/sales' || path.startsWith('/sales/')) {
    return {
      productId: 'salespilot',
      persist: true,
      surface: 'workspace',
      reason: 'route_salespilot',
    }
  }

  if (
    path === '/home' ||
    path.startsWith('/home/') ||
    path.startsWith('/platform') ||
    PLATFORM_EXACT.has(path) ||
    path.startsWith('/admin/')
  ) {
    return {
      productId: 'elfis-core',
      persist: false,
      surface: 'platform',
      reason: 'route_public',
    }
  }

  if (PUBLIC_EXACT.has(path)) {
    return {
      productId: 'elfis-core',
      persist: false,
      surface: 'platform',
      reason: 'route_public',
    }
  }

  if (path.startsWith('/developer')) {
    return {
      productId: 'elfis-core',
      persist: false,
      surface: 'platform',
      reason: 'route_public',
    }
  }

  for (const prefix of COMPTAPILOT_PREFIXES) {
    if (path === prefix || path.startsWith(`${prefix}/`)) {
      return {
        productId: 'comptapilot',
        persist: true,
        surface: 'workspace',
        reason: 'route_comptapilot',
      }
    }
  }

  // Authenticated catch-all under product shell → ComptaPilot
  // Unknown public-ish paths → ELFIS Core (never universal comptapilot)
  return {
    productId: 'elfis-core',
    persist: false,
    surface: 'platform',
    reason: 'route_fallback',
  }
}

function normalizePath(pathname: string): string {
  if (!pathname) return '/'
  const trimmed = pathname.split('?')[0].split('#')[0] || '/'
  if (trimmed.length > 1 && trimmed.endsWith('/')) return trimmed.slice(0, -1)
  return trimmed || '/'
}

/** Minimal token map for pre-React bootstrap (must match PRODUCT_PALETTES). */
export const BOOTSTRAP_PRODUCT_COLORS: Record<
  'elfis-core' | 'comptapilot' | 'salespilot',
  { primary: string; primaryHover: string; accent: string; surface: string; focus: string }
> = {
  'elfis-core': {
    primary: '#071629',
    primaryHover: '#102746',
    accent: '#2764E7',
    surface: '#EAF1FF',
    focus: '#2764E7',
  },
  comptapilot: {
    primary: '#0B3D2E',
    primaryHover: '#07281E',
    accent: '#7BC4A0',
    surface: '#E7F2EC',
    focus: '#7BC4A0',
  },
  salespilot: {
    primary: '#1D4ED8',
    primaryHover: '#1E40AF',
    accent: '#60A5FA',
    surface: '#E8F0FE',
    focus: '#60A5FA',
  },
}
