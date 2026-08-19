import { useContext, useEffect, useState } from 'react'
import { OverlayProviderContext, type OverlayManagerApi } from '../OverlayContext'

/**
 * Public hook — controlled overlays register here; no free stack mutation.
 * Context identity is stable — safe to depend on in effects.
 */
export function useOverlayManager(): OverlayManagerApi {
  const ctx = useContext(OverlayProviderContext)
  if (!ctx) {
    throw new Error('useOverlayManager() doit être utilisé dans OverlayProvider')
  }
  const { manager: _m, stackRevision: _r, ...api } = ctx
  void _m
  void _r
  return api
}

export function useOverlayManagerOptional(): OverlayManagerApi | null {
  const ctx = useContext(OverlayProviderContext)
  if (!ctx) return null
  const { manager: _m, stackRevision: _r, ...api } = ctx
  void _m
  void _r
  return api
}

/** Debug: re-renders when stack changes (sandbox DEV only). */
export function useOverlayStackDebug() {
  const ctx = useContext(OverlayProviderContext)
  const [revision, setRevision] = useState(0)

  useEffect(() => {
    if (!ctx) return
    return ctx.subscribe(() => setRevision((n) => n + 1))
  }, [ctx])

  if (!ctx) {
    return { snapshot: [] as ReturnType<OverlayManagerApi['getDebugSnapshot']>, depth: 0, revision: 0 }
  }
  void revision
  return {
    snapshot: ctx.getDebugSnapshot(),
    depth: ctx.getStackDepth(),
    revision,
  }
}
