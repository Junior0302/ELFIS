/**
 * React Product Theme context + provider + hook.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import { createThemeEngine, type SetProductOptions, type ThemeEngine } from './createThemeEngine'
import type { ProductId, ProductIdentity } from '../types'
import type { ProductTheme } from './interfaces'

export const PRODUCT_THEME_HOOK_ERROR =
  'useProductTheme() doit être utilisé dans un ProductThemeProvider'

export type ProductThemeContextValue = {
  currentProductId: ProductId
  currentTheme: ProductTheme
  /** Prefer setCurrentProductFromRoute for identity; launcher may navigate without calling this. */
  setCurrentProduct: (productId: string) => boolean
  /** Route sync — single authorized writer for runtime identity. */
  setCurrentProductFromRoute: (productId: string, options: SetProductOptions) => boolean
  resetProductTheme: () => void
  isThemeReady: boolean
  availableProducts: ProductIdentity[]
  error: string | null
  /** application = real workspace; preview = design-system sandbox */
  mode: 'application' | 'preview'
}

const ProductThemeContext = createContext<ProductThemeContextValue | null>(null)

export type ProductThemeProviderProps = {
  children: ReactNode
  initialProductId?: ProductId
  allowPreviewUnavailableProducts?: boolean
  persist?: boolean
  /** Apply CSS vars to documentElement (default) or skip / custom target via engine. */
  applyToDom?: boolean
  surface?: 'workspace' | 'platform'
  /** Route-based boot (default true except sandbox). */
  resolveFromPath?: boolean
}

export function ProductThemeProvider({
  children,
  initialProductId,
  allowPreviewUnavailableProducts = false,
  persist = true,
  applyToDom = true,
  surface = 'workspace',
  resolveFromPath = true,
}: ProductThemeProviderProps) {
  const engineRef = useRef<ThemeEngine | null>(null)
  if (!engineRef.current) {
    engineRef.current = createThemeEngine({
      initialProductId,
      allowPreviewUnavailableProducts,
      persist,
      applyToDom,
      surface,
      resolveFromPath: allowPreviewUnavailableProducts ? false : resolveFromPath,
    })
  }

  const engine = engineRef.current
  const [tick, setTick] = useState(0)

  useEffect(() => {
    return () => {
      engine.destroy()
      engineRef.current = null
    }
  }, [engine])

  const setCurrentProductFromRoute = useCallback(
    (productId: string, options: SetProductOptions) => {
      const before = engine.getState().currentProductId
      const ok = engine.setCurrentProduct(productId, options)
      const after = engine.getState().currentProductId
      // Only re-render when identity actually changed
      if (ok && before !== after) {
        setTick((t) => t + 1)
      }
      return ok
    },
    [engine],
  )

  const value = useMemo<ProductThemeContextValue>(() => {
    const state = engine.getState()
    return {
      currentProductId: state.currentProductId,
      currentTheme: state.currentTheme,
      isThemeReady: state.isThemeReady,
      error: state.error,
      mode: state.mode,
      availableProducts: engine.availableProducts(),
      setCurrentProduct: (productId: string) => {
        const before = engine.getState().currentProductId
        const ok = engine.setCurrentProduct(productId)
        const after = engine.getState().currentProductId
        if (ok && before !== after) {
          setTick((t) => t + 1)
        }
        return ok
      },
      setCurrentProductFromRoute,
      resetProductTheme: () => {
        engine.resetProductTheme()
        setTick((t) => t + 1)
      },
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [engine, tick, setCurrentProductFromRoute])

  return (
    <ProductThemeContext.Provider value={value}>{children}</ProductThemeContext.Provider>
  )
}

export function useProductTheme(): ProductThemeContextValue {
  const ctx = useContext(ProductThemeContext)
  if (!ctx) {
    throw new Error(PRODUCT_THEME_HOOK_ERROR)
  }
  return ctx
}

/** Test helper — assert context presence without React. */
export function assertProductThemeContext(
  ctx: ProductThemeContextValue | null,
): asserts ctx is ProductThemeContextValue {
  if (!ctx) throw new Error(PRODUCT_THEME_HOOK_ERROR)
}
