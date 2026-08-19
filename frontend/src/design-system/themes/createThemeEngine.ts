/**
 * Pure Theme Engine runtime controller — testable without React.
 */

import { DEFAULT_RUNTIME_PRODUCT_ID, PRODUCT_REGISTRY, isKnownProductId } from '../products/registry'
import { isProductAvailable } from '../products/helpers'
import { applyProductTheme, clearProductTheme, type ThemeTarget } from './applyProductTheme'
import { emitProductThemeChanged } from './events'
import {
  clearPersistedProductId,
  readPersistedProductId,
  writePersistedProductId,
} from './persistence'
import { resolveProductTheme } from './resolveProductTheme'
import { resolveRuntimeProductFromPath } from './resolveRuntimeProductFromPath'
import type { ProductId, ProductIdentity } from '../types'
import type { ProductTheme } from './interfaces'

export type ThemeEngineMode = 'application' | 'preview'

export type ThemeEngineOptions = {
  initialProductId?: ProductId
  /** Application mode rejects unavailable products. Preview allows all known themes. */
  allowPreviewUnavailableProducts?: boolean
  persist?: boolean
  /** When false, skip DOM writes (unit tests). */
  applyToDom?: boolean
  target?: ThemeTarget | null
  surface?: 'workspace' | 'platform'
  /**
   * When true, resolve initial id from window.location (route wins over forced initial).
   * Default true for application runtime.
   */
  resolveFromPath?: boolean
}

export type ThemeEngineState = {
  currentProductId: ProductId
  currentTheme: ProductTheme
  isThemeReady: boolean
  error: string | null
  mode: ThemeEngineMode
}

export type SetProductOptions = {
  /** Persist business product only when true. */
  persist?: boolean
  reason?: string
  path?: string
  /** Force emit even if id unchanged (rare). */
  force?: boolean
}

export type ThemeEngine = {
  getState(): ThemeEngineState
  setCurrentProduct(productId: string, options?: SetProductOptions): boolean
  resetProductTheme(): void
  availableProducts(): ProductIdentity[]
  destroy(): void
}

function canActivate(productId: ProductId, allowPreview: boolean): boolean {
  // Platform + installed Pilot shells are always themable (route is the gate).
  if (productId === 'elfis-core' || productId === 'comptapilot' || productId === 'salespilot') {
    return true
  }
  if (allowPreview) return true
  return isProductAvailable(productId)
}

function resolveInitialId(options: ThemeEngineOptions): ProductId {
  // Route is the source of truth at boot when running in browser.
  if (options.resolveFromPath !== false && typeof window !== 'undefined') {
    try {
      const fromPath = resolveRuntimeProductFromPath(window.location.pathname || '/')
      if (fromPath.surface !== 'sandbox' && canActivate(fromPath.productId, !!options.allowPreviewUnavailableProducts)) {
        return fromPath.productId
      }
    } catch {
      /* fall through */
    }
  }

  if (options.initialProductId && isKnownProductId(options.initialProductId)) {
    if (canActivate(options.initialProductId, !!options.allowPreviewUnavailableProducts)) {
      return options.initialProductId
    }
  }
  if (options.persist !== false) {
    const stored = readPersistedProductId({
      requireAvailable: !options.allowPreviewUnavailableProducts,
    })
    if (stored.ok) return stored.productId
  }
  return options.surface === 'platform' ? 'elfis-core' : DEFAULT_RUNTIME_PRODUCT_ID
}

export function createThemeEngine(options: ThemeEngineOptions = {}): ThemeEngine {
  const allowPreview = !!options.allowPreviewUnavailableProducts
  const persistDefault = options.persist !== false
  const applyToDom = options.applyToDom !== false
  const mode: ThemeEngineMode = allowPreview ? 'preview' : 'application'

  let currentProductId = resolveInitialId(options)
  let currentTheme = resolveProductTheme(currentProductId, { surface: options.surface })
  let error: string | null = null
  let lastAppliedId: ProductId | null = null

  const apply = (theme: ProductTheme, force = false) => {
    if (!force && lastAppliedId === theme.productId) return
    if (applyToDom) {
      // Atomic apply — no clear-before-set (anti flicker).
      applyProductTheme(theme, options.target)
    }
    lastAppliedId = theme.productId
  }

  apply(currentTheme, true)
  // Persist only business products at boot
  if (persistDefault && !allowPreview && (currentProductId === 'comptapilot' || currentProductId === 'salespilot')) {
    writePersistedProductId(currentProductId)
  }

  return {
    getState(): ThemeEngineState {
      return {
        currentProductId,
        currentTheme,
        isThemeReady: true,
        error,
        mode,
      }
    },

    setCurrentProduct(productId: string, setOptions: SetProductOptions = {}): boolean {
      if (!isKnownProductId(productId)) {
        error = `Produit inconnu: ${productId}`
        return false
      }
      if (!canActivate(productId, allowPreview)) {
        error = `Produit non disponible: ${productId}`
        return false
      }
      if (productId === currentProductId && lastAppliedId === productId && !setOptions.force) {
        error = null
        return true
      }
      const previous = currentProductId
      currentProductId = productId
      currentTheme = resolveProductTheme(productId, { surface: options.surface })
      error = null
      apply(currentTheme, !!setOptions.force)

      const shouldPersist =
        setOptions.persist !== undefined
          ? setOptions.persist
          : persistDefault && !allowPreview && (productId === 'comptapilot' || productId === 'salespilot')

      if (shouldPersist) {
        writePersistedProductId(productId)
      }

      if (previous !== productId) {
        emitProductThemeChanged({
          previousProductId: previous,
          currentProductId: productId,
          themeId: currentTheme.themeId,
        })
      }
      return true
    },

    resetProductTheme(): void {
      const previous = currentProductId
      const fallback =
        options.surface === 'platform' ? ('elfis-core' as ProductId) : DEFAULT_RUNTIME_PRODUCT_ID
      currentProductId = fallback
      currentTheme = resolveProductTheme(fallback, { surface: options.surface })
      error = null
      apply(currentTheme, true)
      if (persistDefault && !allowPreview) {
        writePersistedProductId(fallback)
      } else if (allowPreview) {
        clearPersistedProductId()
      }
      emitProductThemeChanged({
        previousProductId: previous,
        currentProductId: fallback,
        themeId: currentTheme.themeId,
      })
    },

    availableProducts(): ProductIdentity[] {
      if (allowPreview) return [...PRODUCT_REGISTRY]
      return PRODUCT_REGISTRY.filter((p) => isProductAvailable(p.id) || p.id === 'elfis-core')
    },

    destroy(): void {
      // CRITICAL: do not clear DOM tokens on destroy.
      // StrictMode remount would flash :root green defaults (oscillation root cause).
      lastAppliedId = null
      if (!applyToDom) {
        clearProductTheme(options.target)
      }
    },
  }
}
