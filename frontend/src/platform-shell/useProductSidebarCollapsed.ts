import { useCallback, useEffect, useState } from 'react'
import {
  PRODUCT_SIDEBAR_TRANSITION_MS,
  notifyProductShellViewportResize,
  readProductSidebarCollapsedPreference,
  writeProductSidebarCollapsedPreference,
} from './productSidebarCollapse'

/**
 * Préférence UI non sensible — init synchrone (pas de flash).
 * Notifie le viewport après la transition de grille (charts / layout).
 */
export function useProductSidebarCollapsed() {
  const [collapsed, setCollapsedState] = useState(readProductSidebarCollapsedPreference)

  const setCollapsed = useCallback((value: boolean | ((prev: boolean) => boolean)) => {
    setCollapsedState((prev) => {
      const next = typeof value === 'function' ? value(prev) : value
      writeProductSidebarCollapsedPreference(next)
      return next
    })
  }, [])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      notifyProductShellViewportResize({ mirrorWindowResize: true })
    }, PRODUCT_SIDEBAR_TRANSITION_MS + 16)
    return () => window.clearTimeout(timer)
  }, [collapsed])

  return { collapsed, setCollapsed } as const
}
