/**
 * Optional browser event for product theme changes (frontend-only).
 */

import type { ProductId, ThemeId } from '../types'

export const PRODUCT_THEME_CHANGED_EVENT = 'elfis:product-theme-changed'

export type ProductThemeChangedDetail = {
  previousProductId: ProductId | null
  currentProductId: ProductId
  themeId: ThemeId
}

export function emitProductThemeChanged(detail: ProductThemeChangedDetail): void {
  if (typeof window === 'undefined' || typeof CustomEvent === 'undefined') return
  window.dispatchEvent(new CustomEvent(PRODUCT_THEME_CHANGED_EVENT, { detail }))
}
