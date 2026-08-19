import {
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  type ReactNode,
} from 'react'
import { createOverlayManager, type OverlayManager } from './manager/overlayManager'
import { bindOverlayCloseAll } from './manager/overlayLifecycle'
import { lockBodyScroll } from './utils/scrollLock'
import { OVERLAY_ROOT_ID } from './utils/zIndex'
import {
  OverlayProviderContext,
  type OverlayProviderContextValue,
} from './OverlayContext'
import type { RegisterOverlayInput, OverlayDescriptor, OverlayCloseReason } from './manager/types'

function ensureOverlayRoot(): HTMLElement | null {
  if (typeof document === 'undefined') return null
  const existing = document.getElementById(OVERLAY_ROOT_ID)
  if (existing instanceof HTMLElement) return existing
  const el = document.createElement('div')
  el.id = OVERLAY_ROOT_ID
  el.className = 'elfis-overlay-root'
  el.setAttribute('data-overlay-root', 'true')
  document.body.appendChild(el)
  return el
}

/**
 * Root overlay orchestrator — Portal root, stack, scroll lock, Escape top-only.
 * Context value is intentionally stable (no stackRevision) to avoid
 * register → notify → re-render → re-register loops.
 */
export function OverlayProvider({ children }: { children: ReactNode }) {
  const portalRootRef = useRef<HTMLElement | null>(null)
  if (portalRootRef.current === null) {
    portalRootRef.current = ensureOverlayRoot()
  }
  const portalRoot = portalRootRef.current

  const managerRef = useRef<OverlayManager>(createOverlayManager())
  const lockReleaseRef = useRef<(() => void) | null>(null)

  const syncScrollLock = useCallback(() => {
    const count = managerRef.current.getModalLockCount()
    if (count > 0 && !lockReleaseRef.current) {
      lockReleaseRef.current = lockBodyScroll()
    } else if (count === 0 && lockReleaseRef.current) {
      lockReleaseRef.current()
      lockReleaseRef.current = null
    }
  }, [])

  useEffect(() => {
    const manager = managerRef.current
    const unsub = manager.subscribe(() => {
      syncScrollLock()
    })
    bindOverlayCloseAll((reason) => {
      manager.closeAll(reason)
      syncScrollLock()
    })
    syncScrollLock()
    return () => {
      unsub()
      bindOverlayCloseAll(null)
      manager.closeAll('provider_unmount')
      if (lockReleaseRef.current) {
        lockReleaseRef.current()
        lockReleaseRef.current = null
      }
    }
  }, [syncScrollLock])

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return
      const top = managerRef.current.getTopOverlay()
      if (!top) return
      if (!top.dismissible || !top.closeOnEscape) return
      const closed = managerRef.current.closeTop('escape')
      if (closed) {
        event.preventDefault()
        event.stopPropagation()
      }
    }
    if (typeof document === 'undefined') return
    document.addEventListener('keydown', onKeyDown, true)
    return () => document.removeEventListener('keydown', onKeyDown, true)
  }, [])

  const value = useMemo<OverlayProviderContextValue>(() => {
    const manager = managerRef.current
    return {
      manager,
      stackRevision: 0,
      portalRoot,
      registerOverlay: (input: RegisterOverlayInput) => {
        const d = manager.registerOverlay(input)
        syncScrollLock()
        return d
      },
      updateOverlay: (id: string, updates: Partial<OverlayDescriptor>) => {
        manager.updateOverlay(id, updates)
        syncScrollLock()
      },
      unregisterOverlay: (id: string) => {
        manager.unregisterOverlay(id)
        syncScrollLock()
      },
      requestClose: (id: string, reason?: OverlayCloseReason) => {
        const ok = manager.requestClose(id, reason)
        syncScrollLock()
        return ok
      },
      closeTop: (reason?: OverlayCloseReason) => {
        const ok = manager.closeTop(reason)
        syncScrollLock()
        return ok
      },
      closeAll: (reason?: OverlayCloseReason) => {
        manager.closeAll(reason)
        syncScrollLock()
      },
      isOpen: (id) => manager.isOpen(id),
      isTopOverlay: (id) => manager.isTopOverlay(id),
      getTopOverlay: () => manager.getTopOverlay(),
      getStack: () => manager.getStack(),
      getStackDepth: () => manager.getStackDepth(),
      getModalLockCount: () => manager.getModalLockCount(),
      getDebugSnapshot: () => manager.getDebugSnapshot(),
      subscribe: (listener) => manager.subscribe(listener),
    }
  }, [portalRoot, syncScrollLock])

  return (
    <OverlayProviderContext.Provider value={value}>{children}</OverlayProviderContext.Provider>
  )
}

/** @deprecated Prefer useOverlayManager — kept for Portal / internal compat. */
export function useOverlayContext() {
  const ctx = useContext(OverlayProviderContext)
  if (!ctx) {
    throw new Error('useOverlayContext() doit être utilisé dans OverlayProvider')
  }
  return ctx
}

export function useOverlayContextOptional() {
  return useContext(OverlayProviderContext)
}

export type { OverlayType as OverlayKind, OverlayDescriptor as OverlayEntry } from './manager/types'
