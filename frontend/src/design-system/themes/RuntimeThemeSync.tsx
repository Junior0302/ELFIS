/**
 * Syncs ProductThemeProvider with the real route — single writer in the app tree.
 */

import { useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import { useProductTheme } from './ProductThemeProvider'
import { resolveRuntimeProductFromPath } from './resolveRuntimeProductFromPath'
import { logThemeChange, trackThemeOscillation } from './themeDevDiagnostics'

/**
 * Must render inside BrowserRouter + ProductThemeProvider.
 * Layouts must not call setCurrentProduct for route identity.
 */
export function RuntimeThemeSync() {
  const location = useLocation()
  const { currentProductId, setCurrentProductFromRoute } = useProductTheme()
  const lastPathRef = useRef<string | null>(null)

  useEffect(() => {
    const resolution = resolveRuntimeProductFromPath(location.pathname)
    if (resolution.surface === 'sandbox') {
      // Sandbox preview owns its nested provider — do not touch root runtime.
      lastPathRef.current = location.pathname
      return
    }

    if (resolution.productId === currentProductId) {
      lastPathRef.current = location.pathname
      return
    }

    const from = currentProductId
    const ok = setCurrentProductFromRoute(resolution.productId, {
      persist: resolution.persist,
      reason: 'route_change',
      path: location.pathname,
    })
    if (ok) {
      logThemeChange({
        from,
        to: resolution.productId,
        reason: 'route_change',
        path: location.pathname,
      })
      trackThemeOscillation(location.pathname)
    }
    lastPathRef.current = location.pathname
  }, [location.pathname, currentProductId, setCurrentProductFromRoute])

  return null
}
