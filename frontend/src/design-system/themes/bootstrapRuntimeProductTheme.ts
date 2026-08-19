/**
 * Pre-React theme bootstrap — applies the same product tokens React will use.
 * Must run before createRoot. Does not create a second theme engine.
 */

import {
  BOOTSTRAP_PRODUCT_COLORS,
  resolveRuntimeProductFromPath,
} from './resolveRuntimeProductFromPath'

/**
 * Reads location.pathname, resolves product, applies minimal --pilot-* + data-product.
 * Idempotent: safe to call again (React will apply the full theme next).
 */
export function bootstrapRuntimeProductTheme(): void {
  if (typeof document === 'undefined' || typeof window === 'undefined') return

  const path = window.location.pathname || '/'
  const { productId } = resolveRuntimeProductFromPath(path)
  const key = productId as keyof typeof BOOTSTRAP_PRODUCT_COLORS
  const colors = BOOTSTRAP_PRODUCT_COLORS[key] ?? BOOTSTRAP_PRODUCT_COLORS['elfis-core']

  const root = document.documentElement
  root.style.setProperty('--pilot-primary', colors.primary)
  root.style.setProperty('--pilot-primary-hover', colors.primaryHover)
  root.style.setProperty('--pilot-primary-active', colors.primaryHover)
  root.style.setProperty('--pilot-primary-contrast', '#ffffff')
  root.style.setProperty('--pilot-accent', colors.accent)
  root.style.setProperty('--pilot-accent-soft', colors.surface)
  root.style.setProperty('--pilot-surface', colors.surface)
  root.style.setProperty('--pilot-surface-hover', colors.surface)
  root.style.setProperty('--pilot-secondary', colors.surface)
  root.style.setProperty('--pilot-border', colors.primary)
  root.style.setProperty('--pilot-focus', colors.focus)
  root.setAttribute('data-product', productId)
  root.setAttribute('data-theme', productId)
  root.setAttribute('data-color-scheme', 'light')
}
