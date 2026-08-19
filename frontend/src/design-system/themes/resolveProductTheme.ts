/**
 * Pure theme resolver — ProductIdentity → ProductTheme.
 * No React dependency.
 */

import { DEFAULT_RUNTIME_PRODUCT_ID, isKnownProductId, getProductById } from '../products/registry'
import { buildPilotTokens } from '../tokens/pilotTokens'
import { validateProductTheme } from './validateProductTheme'
import type { ProductId } from '../types'
import type { ProductTheme, ResolveProductThemeOptions } from './interfaces'

function devWarn(message: string, detail?: unknown): void {
  if (typeof import.meta !== 'undefined' && import.meta.env?.DEV) {
    // eslint-disable-next-line no-console
    console.warn(`[ELFIS ThemeEngine] ${message}`, detail ?? '')
  }
}

function fallbackProductId(surface: ResolveProductThemeOptions['surface']): ProductId {
  return surface === 'platform' ? 'elfis-core' : DEFAULT_RUNTIME_PRODUCT_ID
}

function buildTheme(
  productId: ProductId,
  meta: { resolvedFromFallback: boolean; requestedProductId?: string },
): ProductTheme {
  const product = getProductById(productId)
  const tokens = buildPilotTokens(productId)
  return {
    productId,
    themeId: product.themeId,
    colorScheme: 'light',
    tokens,
    branding: {
      ...product.branding,
      displayName: product.displayName,
      shortName: product.shortName,
    },
    metadata: {
      status: product.status,
      category: product.category,
      tagline: product.tagline,
      accentGradient: product.accentGradient,
      resolvedFromFallback: meta.resolvedFromFallback,
      requestedProductId: meta.requestedProductId,
    },
    product,
  }
}

/**
 * Resolves a complete ProductTheme from a product id.
 * Unknown ids never throw — they fall back to ComptaPilot (workspace) or ELFIS Core (platform).
 */
export function resolveProductTheme(
  productId: string,
  options: ResolveProductThemeOptions = {},
): ProductTheme {
  const surface = options.surface ?? 'workspace'
  let resolvedId: ProductId
  let resolvedFromFallback = false
  let requestedProductId: string | undefined

  if (isKnownProductId(productId)) {
    resolvedId = productId
  } else {
    resolvedId = fallbackProductId(surface)
    resolvedFromFallback = true
    requestedProductId = productId
    devWarn(`Unknown productId "${productId}", falling back to "${resolvedId}"`)
  }

  let theme = buildTheme(resolvedId, { resolvedFromFallback, requestedProductId })
  const validation = validateProductTheme(theme)

  if (!validation.ok) {
    const isProd =
      typeof import.meta !== 'undefined' && import.meta.env?.PROD === true
    if (!isProd) {
      throw new Error(
        `[ELFIS ThemeEngine] Invalid theme for ${resolvedId}: ${validation.issues
          .map((i) => i.message)
          .join('; ')}`,
      )
    }
    devWarn('Theme validation failed in production — using ComptaPilot fallback', validation.issues)
    theme = buildTheme(DEFAULT_RUNTIME_PRODUCT_ID, {
      resolvedFromFallback: true,
      requestedProductId: productId,
    })
  }

  return theme
}
