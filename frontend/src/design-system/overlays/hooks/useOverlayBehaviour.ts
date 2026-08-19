import { useEffect, useId, useLayoutEffect, useRef } from 'react'
import { useOverlayContextOptional } from '../OverlayProvider'
import { useOverlayParentId } from '../OverlayContext'
import { focusFirstElement, restoreFocus, trapTabKey } from '../utils/focus'
import type { OverlayCloseReason, OverlayType } from '../manager/types'

export type UseOverlayBehaviourOptions = {
  open: boolean
  type: OverlayType
  modal?: boolean
  dismissible?: boolean
  closeOnEscape?: boolean
  closeOnBackdrop?: boolean
  closeOnRouteChange?: boolean
  onClose: (reason?: OverlayCloseReason) => void
  panelRef: React.RefObject<HTMLElement | null>
  initialFocusRef?: React.RefObject<HTMLElement | null>
  returnFocusRef?: React.RefObject<HTMLElement | null>
  lockScroll?: boolean
  parentOverlayId?: string
}

/**
 * Registers with OverlayManager; Escape is handled by OverlayProvider (single listener).
 * Focus trap only when this instance is the top overlay.
 */
export function useOverlayBehaviour({
  open,
  type,
  modal = true,
  dismissible = true,
  closeOnEscape = true,
  closeOnBackdrop = true,
  closeOnRouteChange,
  onClose,
  panelRef,
  initialFocusRef,
  returnFocusRef,
  lockScroll = modal,
  parentOverlayId: parentProp,
}: UseOverlayBehaviourOptions): { overlayId: string } {
  const ctx = useOverlayContextOptional()
  const inheritedParent = useOverlayParentId()
  const parentOverlayId = parentProp ?? inheritedParent ?? undefined
  const id = useId()
  const triggerRef = useRef<HTMLElement | null>(null)
  const wasOpenRef = useRef(false)
  const onCloseRef = useRef(onClose)
  onCloseRef.current = onClose

  useEffect(() => {
    if (!open || !ctx) return
    triggerRef.current =
      (typeof document !== 'undefined' ? (document.activeElement as HTMLElement) : null) || null

    ctx.registerOverlay({
      id,
      type,
      modal,
      dismissible,
      closeOnEscape,
      closeOnBackdrop,
      closeOnRouteChange,
      parentOverlayId,
      triggerElement: triggerRef.current,
      lockScroll,
      restoreFocus: true,
      onRequestClose: (reason: OverlayCloseReason) => {
        onCloseRef.current(reason)
      },
    })
    return () => ctx.unregisterOverlay(id)
  }, [
    open,
    id,
    type,
    modal,
    dismissible,
    closeOnEscape,
    closeOnBackdrop,
    closeOnRouteChange,
    parentOverlayId,
    lockScroll,
    ctx,
  ])

  useLayoutEffect(() => {
    if (!open || !modal) return
    let cancelled = false
    const tryFocus = (): boolean => {
      if (cancelled) return false
      const panel = panelRef.current
      if (!panel) return false
      if (initialFocusRef?.current) {
        initialFocusRef.current.focus()
        return document.activeElement === initialFocusRef.current
      }
      focusFirstElement(panel)
      return true
    }
    if (tryFocus()) {
      return () => {
        cancelled = true
      }
    }
    const t0 = window.setTimeout(tryFocus, 0)
    const t1 = window.setTimeout(tryFocus, 16)
    return () => {
      cancelled = true
      window.clearTimeout(t0)
      window.clearTimeout(t1)
    }
  }, [open, modal, panelRef, initialFocusRef])

  useEffect(() => {
    if (!open || !modal) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Tab') return
      const isTop = ctx ? ctx.isTopOverlay(id) : true
      if (!isTop || !panelRef.current) return
      trapTabKey(event, panelRef.current)
    }
    if (typeof document === 'undefined') return
    document.addEventListener('keydown', onKeyDown, true)
    return () => document.removeEventListener('keydown', onKeyDown, true)
  }, [open, ctx, id, modal, panelRef])

  useEffect(() => {
    if (open) {
      wasOpenRef.current = true
      return
    }
    if (!wasOpenRef.current) return
    wasOpenRef.current = false
    if (ctx?.manager.isBulkClosing()) return

    const parentStillOpen =
      parentOverlayId &&
      ctx?.getStack().some((d) => d.id === parentOverlayId && d.status !== 'closing')
    if (parentStillOpen) return

    const target = returnFocusRef?.current ?? triggerRef.current
    restoreFocus(target)
  }, [open, returnFocusRef, ctx, parentOverlayId])

  return { overlayId: id }
}
