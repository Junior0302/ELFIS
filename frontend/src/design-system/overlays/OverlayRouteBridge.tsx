import { useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import { useOverlayContextOptional } from './OverlayProvider'

/**
 * Closes overlays with closeOnRouteChange on pathname/search change.
 * Must render inside BrowserRouter + OverlayProvider.
 */
export function OverlayRouteBridge() {
  const ctx = useOverlayContextOptional()
  const location = useLocation()
  const prevKey = useRef(`${location.pathname}${location.search}`)

  useEffect(() => {
    const key = `${location.pathname}${location.search}`
    if (key === prevKey.current) return
    prevKey.current = key
    if (!ctx) return

    const stack = ctx.getStack()
    for (const d of [...stack].reverse()) {
      if (d.closeOnRouteChange) {
        ctx.requestClose(d.id, 'route_change')
      }
    }
  }, [location.pathname, location.search, ctx])

  return null
}
