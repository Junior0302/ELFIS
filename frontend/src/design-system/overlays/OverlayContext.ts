import { createContext, useContext } from 'react'
import type { OverlayManager } from './manager/overlayManager'
import type { OverlayDescriptor, OverlayCloseReason, OverlayStackSnapshot } from './manager/types'

/**
 * Public API surface for useOverlayManager().
 * Mutations of the raw stack are not exposed.
 */
export type OverlayManagerApi = {
  registerOverlay: OverlayManager['registerOverlay']
  updateOverlay: OverlayManager['updateOverlay']
  unregisterOverlay: OverlayManager['unregisterOverlay']
  requestClose: (id: string, reason?: OverlayCloseReason) => boolean
  closeTop: (reason?: OverlayCloseReason) => boolean
  closeAll: (reason?: OverlayCloseReason) => void
  isOpen: (id: string) => boolean
  isTopOverlay: (id: string) => boolean
  getTopOverlay: () => OverlayDescriptor | null
  getStack: () => readonly OverlayDescriptor[]
  getStackDepth: () => number
  getModalLockCount: () => number
  getDebugSnapshot: () => OverlayStackSnapshot[]
  portalRoot: HTMLElement | null
  /** Subscribe to stack changes (debug / tests). */
  subscribe: (listener: () => void) => () => void
}

export type OverlayProviderContextValue = OverlayManagerApi & {
  manager: OverlayManager
  /** React revision bump for consumers that need re-render on stack change. */
  stackRevision: number
}

export const OverlayProviderContext = createContext<OverlayProviderContextValue | null>(null)

/** Nested overlay parent id (Dialog → Popover). */
export const OverlayParentIdContext = createContext<string | null>(null)

export function useOverlayParentId(): string | null {
  return useContext(OverlayParentIdContext)
}
