import type { ProductId } from '../design-system'

const LAST_PRODUCT_KEY = 'elfis_last_product'
const LAST_PRODUCT_AT_KEY = 'elfis_last_product_at'

const KNOWN: ProductId[] = ['comptapilot', 'salespilot']

export function getLastProductId(): ProductId | null {
  try {
    const raw = localStorage.getItem(LAST_PRODUCT_KEY)
    if (raw && (KNOWN as string[]).includes(raw)) return raw as ProductId
  } catch {
    /* ignore */
  }
  return null
}

export function setLastProductId(productId: ProductId): void {
  if (!(KNOWN as string[]).includes(productId)) return
  try {
    localStorage.setItem(LAST_PRODUCT_KEY, productId)
    localStorage.setItem(LAST_PRODUCT_AT_KEY, new Date().toISOString())
  } catch {
    /* ignore */
  }
}

export function getLastProductAt(): string | null {
  try {
    return localStorage.getItem(LAST_PRODUCT_AT_KEY)
  } catch {
    return null
  }
}
