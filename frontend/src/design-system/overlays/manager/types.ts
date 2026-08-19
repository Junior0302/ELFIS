/**
 * Overlay Orchestrator — types (E1.4.1)
 * Pure descriptors; no React content stored in the registry.
 */

export type OverlayType =
  | 'tooltip'
  | 'popover'
  | 'drawer'
  | 'dialog'
  | 'confirm_dialog'
  | 'critical_dialog'
  | 'custom'

export type OverlayPriority = 'passive' | 'floating' | 'panel' | 'modal' | 'critical'

export type OverlayStatus = 'opening' | 'open' | 'closing'

export type OverlayCloseReason =
  | 'escape'
  | 'backdrop'
  | 'action'
  | 'cancel'
  | 'route_change'
  | 'logout'
  | 'organization_change'
  | 'product_change'
  | 'provider_unmount'
  | 'programmatic'
  | 'parent_closed'

export type OverlayDescriptor = {
  id: string
  type: OverlayType
  priority: OverlayPriority
  modal: boolean
  dismissible: boolean
  closeOnEscape: boolean
  closeOnBackdrop: boolean
  closeOnRouteChange: boolean
  openedAt: number
  parentOverlayId?: string
  /** Soft reference — may be detached from DOM. */
  triggerElement?: HTMLElement | null
  metadata?: Record<string, string | number | boolean | null>
  onRequestClose: (reason: OverlayCloseReason) => void
  restoreFocus?: boolean
  lockScroll: boolean
  status: OverlayStatus
}

/** Input for register — defaults filled by manager. */
export type RegisterOverlayInput = {
  id: string
  type: OverlayType
  priority?: OverlayPriority
  modal?: boolean
  dismissible?: boolean
  closeOnEscape?: boolean
  closeOnBackdrop?: boolean
  closeOnRouteChange?: boolean
  parentOverlayId?: string
  triggerElement?: HTMLElement | null
  metadata?: OverlayDescriptor['metadata']
  onRequestClose: (reason: OverlayCloseReason) => void
  restoreFocus?: boolean
  lockScroll?: boolean
  status?: OverlayStatus
}

export type OverlayStackSnapshot = {
  id: string
  type: OverlayType
  priority: OverlayPriority
  modal: boolean
  dismissible: boolean
  depth: number
  isTop: boolean
}

export const OVERLAY_EVENT = {
  opened: 'elfis:overlay-opened',
  closed: 'elfis:overlay-closed',
  stackChanged: 'elfis:overlay-stack-changed',
} as const

export type OverlayEventDetail = {
  overlayId: string
  overlayType: OverlayType
  priority: OverlayPriority
  stackDepth: number
  reason?: OverlayCloseReason
}
