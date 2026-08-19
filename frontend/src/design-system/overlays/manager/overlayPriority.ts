import type { OverlayPriority, OverlayType } from './types'
import { OVERLAY_Z } from '../utils/zIndex'

const PRIORITY_RANK: Record<OverlayPriority, number> = {
  passive: 1,
  floating: 2,
  panel: 3,
  modal: 4,
  critical: 5,
}

const PRIORITY_BASE_Z: Record<OverlayPriority, number> = {
  passive: OVERLAY_Z.tooltip,
  floating: OVERLAY_Z.popover,
  panel: OVERLAY_Z.drawer,
  modal: OVERLAY_Z.dialog,
  critical: OVERLAY_Z.critical,
}

/** Default priority from overlay type (+ modal flag for drawers). */
export function resolvePriority(
  type: OverlayType,
  options?: { modal?: boolean },
): OverlayPriority {
  switch (type) {
    case 'tooltip':
      return 'passive'
    case 'popover':
      return 'floating'
    case 'drawer':
      return options?.modal === false ? 'panel' : 'modal'
    case 'dialog':
    case 'confirm_dialog':
      return 'modal'
    case 'critical_dialog':
      return 'critical'
    case 'custom':
      return options?.modal ? 'modal' : 'floating'
    default:
      return 'modal'
  }
}

export function comparePriority(a: OverlayPriority, b: OverlayPriority): number {
  return PRIORITY_RANK[a] - PRIORITY_RANK[b]
}

export function priorityRank(priority: OverlayPriority): number {
  return PRIORITY_RANK[priority]
}

/**
 * Deterministic z-index: priority base + controlled depth (0..9).
 * Never uses arbitrary 999999 values.
 */
export function computeOverlayZIndex(priority: OverlayPriority, depthInPriorityBand: number): number {
  const base = PRIORITY_BASE_Z[priority]
  const depth = Math.max(0, Math.min(9, depthInPriorityBand))
  return base + depth
}

export function defaultCloseOnRouteChange(type: OverlayType): boolean {
  return (
    type === 'tooltip' ||
    type === 'popover' ||
    type === 'drawer' ||
    type === 'dialog' ||
    type === 'confirm_dialog' ||
    type === 'critical_dialog' ||
    type === 'custom'
  )
}
