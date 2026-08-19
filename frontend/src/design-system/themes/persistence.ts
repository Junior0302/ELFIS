/**
 * Persist only the stable product id — never the full theme.
 */

import { isKnownProductId } from '../products/registry'
import { isProductAvailable } from '../products/helpers'
import type { ProductId } from '../types'

export const PRODUCT_THEME_STORAGE_KEY = 'elfis.design-system.current-product'

export type PersistReadResult =
  | { ok: true; productId: ProductId }
  | { ok: false; reason: 'missing' | 'invalid' | 'unavailable' }

function storage(): Storage | null {
  try {
    if (typeof localStorage === 'undefined') return null
    return localStorage
  } catch {
    return null
  }
}

export function readPersistedProductId(options?: {
  /** When false, reject coming_soon / archived / internal. */
  requireAvailable?: boolean
}): PersistReadResult {
  const requireAvailable = options?.requireAvailable ?? true
  const store = storage()
  if (!store) return { ok: false, reason: 'missing' }
  let raw: string | null
  try {
    raw = store.getItem(PRODUCT_THEME_STORAGE_KEY)
  } catch {
    return { ok: false, reason: 'missing' }
  }
  if (!raw) return { ok: false, reason: 'missing' }
  if (!isKnownProductId(raw)) return { ok: false, reason: 'invalid' }
  if (requireAvailable && !isProductAvailable(raw)) {
    return { ok: false, reason: 'unavailable' }
  }
  return { ok: true, productId: raw }
}

export function writePersistedProductId(productId: ProductId): void {
  const store = storage()
  if (!store) return
  try {
    store.setItem(PRODUCT_THEME_STORAGE_KEY, productId)
  } catch {
    /* quota / private mode */
  }
}

export function clearPersistedProductId(): void {
  const store = storage()
  if (!store) return
  try {
    store.removeItem(PRODUCT_THEME_STORAGE_KEY)
  } catch {
    /* ignore */
  }
}
