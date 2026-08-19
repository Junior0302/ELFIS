import type { OverlayCloseReason, OverlayEventDetail, OverlayType, OverlayPriority } from './types'
import { OVERLAY_EVENT } from './types'

function canEmit(): boolean {
  return typeof window !== 'undefined' && typeof window.dispatchEvent === 'function'
}

export function emitOverlayOpened(detail: OverlayEventDetail): void {
  if (!canEmit()) return
  window.dispatchEvent(new CustomEvent(OVERLAY_EVENT.opened, { detail }))
}

export function emitOverlayClosed(detail: OverlayEventDetail): void {
  if (!canEmit()) return
  window.dispatchEvent(new CustomEvent(OVERLAY_EVENT.closed, { detail }))
}

export function emitOverlayStackChanged(detail: {
  stackDepth: number
  topId: string | null
  topType: OverlayType | null
  topPriority: OverlayPriority | null
}): void {
  if (!canEmit()) return
  window.dispatchEvent(
    new CustomEvent(OVERLAY_EVENT.stackChanged, {
      detail: {
        overlayId: detail.topId ?? '',
        overlayType: detail.topType ?? 'custom',
        priority: detail.topPriority ?? 'passive',
        stackDepth: detail.stackDepth,
      } satisfies OverlayEventDetail,
    }),
  )
}

/** Guard: events must never carry business / PII payloads. */
export function assertSafeEventDetail(detail: OverlayEventDetail): boolean {
  const keys = Object.keys(detail)
  const allowed = new Set(['overlayId', 'overlayType', 'priority', 'stackDepth', 'reason'])
  return keys.every((k) => allowed.has(k))
}

export type { OverlayCloseReason }
