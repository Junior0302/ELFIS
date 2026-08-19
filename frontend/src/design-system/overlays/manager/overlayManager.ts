import type {
  OverlayCloseReason,
  OverlayDescriptor,
  OverlayStackSnapshot,
  RegisterOverlayInput,
} from './types'
import { defaultCloseOnRouteChange, resolvePriority } from './overlayPriority'
import {
  closeAllOrder,
  closeOrderForParent,
  cloneStack,
  getTop,
  isTop,
  removeDescriptor,
  updateDescriptor,
  upsertDescriptor,
} from './overlayStack'
import { emitOverlayClosed, emitOverlayOpened, emitOverlayStackChanged } from './overlayEvents'

/** Reasons that force-close even when dismissible=false. */
const FORCE_CLOSE_REASONS: ReadonlySet<OverlayCloseReason> = new Set([
  'logout',
  'organization_change',
  'product_change',
  'provider_unmount',
  'parent_closed',
  'programmatic',
  'route_change',
])

/** Escape / backdrop only apply to the top dismissible overlay. */
const TOP_ONLY_REASONS: ReadonlySet<OverlayCloseReason> = new Set(['escape', 'backdrop'])

export type OverlayManager = {
  registerOverlay: (input: RegisterOverlayInput) => OverlayDescriptor
  updateOverlay: (id: string, updates: Partial<OverlayDescriptor>) => void
  unregisterOverlay: (id: string) => void
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
  subscribe: (listener: () => void) => () => void
  /** Bulk close in progress — skip per-overlay focus restore. */
  isBulkClosing: () => boolean
  dispose: () => void
}

export type CreateOverlayManagerOptions = {
  /** When false, skip CustomEvent emissions (SSR / unit tests). Default: true if window exists. */
  emitEvents?: boolean
  now?: () => number
}

export function createOverlayManager(options: CreateOverlayManagerOptions = {}): OverlayManager {
  let stack: OverlayDescriptor[] = []
  const listeners = new Set<() => void>()
  let bulkClosing = false
  let disposed = false
  const closingIds = new Set<string>()
  let seq = 0
  const emitEvents =
    options.emitEvents ?? (typeof window !== 'undefined')
  const now = options.now ?? (() => Date.now())

  const notify = () => {
    for (const l of listeners) l()
    if (!emitEvents) return
    const top = getTop(stack)
    emitOverlayStackChanged({
      stackDepth: stack.length,
      topId: top?.id ?? null,
      topType: top?.type ?? null,
      topPriority: top?.priority ?? null,
    })
  }

  const setStack = (next: OverlayDescriptor[]) => {
    stack = next
    notify()
  }

  const normalize = (input: RegisterOverlayInput): OverlayDescriptor => {
    const modal = input.modal ?? (input.type !== 'tooltip' && input.type !== 'popover')
    const priority = input.priority ?? resolvePriority(input.type, { modal })
    seq += 1
    return {
      id: input.id,
      type: input.type,
      priority,
      modal,
      dismissible: input.dismissible ?? true,
      closeOnEscape: input.closeOnEscape ?? true,
      closeOnBackdrop: input.closeOnBackdrop ?? true,
      closeOnRouteChange: input.closeOnRouteChange ?? defaultCloseOnRouteChange(input.type),
      openedAt: now() * 1000 + seq,
      parentOverlayId: input.parentOverlayId,
      triggerElement: input.triggerElement ?? null,
      metadata: input.metadata,
      onRequestClose: input.onRequestClose,
      restoreFocus: input.restoreFocus ?? true,
      lockScroll: input.lockScroll ?? modal,
      status: input.status ?? 'open',
    }
  }

  const canClose = (d: OverlayDescriptor, reason: OverlayCloseReason): boolean => {
    if (closingIds.has(d.id) || d.status === 'closing') return false
    if (FORCE_CLOSE_REASONS.has(reason)) return true
    if (!d.dismissible) return false
    if (reason === 'escape' && !d.closeOnEscape) return false
    if (reason === 'backdrop' && !d.closeOnBackdrop) return false
    if (TOP_ONLY_REASONS.has(reason) && !isTop(stack, d.id)) return false
    return true
  }

  const invokeClose = (id: string, reason: OverlayCloseReason): boolean => {
    const d = stack.find((x) => x.id === id)
    if (!d) return false
    if (!canClose(d, reason)) return false

    closingIds.add(id)
    setStack(updateDescriptor(stack, id, { status: 'closing' }))

    try {
      d.onRequestClose(reason)
    } catch {
      /* caller errors must not break stack */
    }

    if (emitEvents) {
      emitOverlayClosed({
        overlayId: d.id,
        overlayType: d.type,
        priority: d.priority,
        stackDepth: Math.max(0, stack.length - 1),
        reason,
      })
    }
    return true
  }

  const api: OverlayManager = {
    registerOverlay(input) {
      if (disposed) return normalize(input)
      if (stack.some((d) => d.id === input.id)) {
        /* Unique IDs: update in place rather than duplicate */
        const existing = stack.find((d) => d.id === input.id)!
        const merged = normalize({ ...input, id: existing.id })
        merged.openedAt = existing.openedAt
        setStack(upsertDescriptor(stack, merged))
        return merged
      }
      const descriptor = normalize(input)
      setStack(upsertDescriptor(stack, descriptor))
      if (emitEvents) {
        emitOverlayOpened({
          overlayId: descriptor.id,
          overlayType: descriptor.type,
          priority: descriptor.priority,
          stackDepth: stack.length,
        })
      }
      return descriptor
    },

    updateOverlay(id, updates) {
      if (disposed || !stack.some((d) => d.id === id)) return
      const { id: _ignore, ...rest } = updates as Partial<OverlayDescriptor> & { id?: string }
      void _ignore
      setStack(updateDescriptor(stack, id, rest))
    },

    unregisterOverlay(id) {
      if (disposed) return
      closingIds.delete(id)
      if (!stack.some((d) => d.id === id)) return
      setStack(removeDescriptor(stack, id))
    },

    requestClose(id, reason = 'programmatic') {
      if (disposed) return false
      const d = stack.find((x) => x.id === id)
      if (!d) return false

      /* Closing a parent also closes descendants first */
      if (collectHasChildren(stack, id)) {
        const order = closeOrderForParent(stack, id)
        let any = false
        for (const childId of order) {
          if (childId === id) {
            any = invokeClose(id, reason) || any
          } else {
            any = invokeClose(childId, 'parent_closed') || any
          }
        }
        return any
      }

      return invokeClose(id, reason)
    },

    closeTop(reason = 'programmatic') {
      const top = getTop(stack)
      if (!top) return false
      if (!top.dismissible && !FORCE_CLOSE_REASONS.has(reason)) return false
      return api.requestClose(top.id, reason)
    },

    closeAll(reason = 'programmatic') {
      if (disposed) return
      bulkClosing = true
      const order = closeAllOrder(stack)
      for (const id of order) {
        invokeClose(id, reason)
      }
      /* Hard clear — components may unmount without unregister */
      closingIds.clear()
      setStack([])
      bulkClosing = false
    },

    isOpen(id) {
      return stack.some((d) => d.id === id && d.status !== 'closing')
    },

    isTopOverlay(id) {
      return isTop(stack, id)
    },

    getTopOverlay() {
      return getTop(stack)
    },

    getStack() {
      return cloneStack(stack)
    },

    getStackDepth() {
      return stack.length
    },

    getModalLockCount() {
      return stack.filter((d) => d.lockScroll && d.status !== 'closing').length
    },

    getDebugSnapshot() {
      const top = getTop(stack)
      return stack.map((d, index) => ({
        id: d.id,
        type: d.type,
        priority: d.priority,
        modal: d.modal,
        dismissible: d.dismissible,
        depth: index,
        isTop: top?.id === d.id,
      }))
    },

    subscribe(listener) {
      listeners.add(listener)
      return () => listeners.delete(listener)
    },

    isBulkClosing() {
      return bulkClosing
    },

    dispose() {
      disposed = true
      bulkClosing = true
      stack = []
      closingIds.clear()
      listeners.clear()
      bulkClosing = false
    },
  }

  return api
}

function collectHasChildren(stack: readonly OverlayDescriptor[], parentId: string): boolean {
  return stack.some((d) => d.parentOverlayId === parentId)
}
