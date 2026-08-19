import {
  comparePriority,
} from './overlayPriority'
import type { OverlayDescriptor } from './types'

/**
 * Pure stack helpers — no React, no DOM.
 * Stack order: index 0 = bottom, last = top overlay.
 */

export function cloneStack(stack: readonly OverlayDescriptor[]): OverlayDescriptor[] {
  return stack.map((d) => ({ ...d }))
}

/** Insert or replace by id, then re-sort. */
export function upsertDescriptor(
  stack: readonly OverlayDescriptor[],
  descriptor: OverlayDescriptor,
): OverlayDescriptor[] {
  const without = stack.filter((d) => d.id !== descriptor.id)
  return sortStack([...without, descriptor])
}

export function removeDescriptor(
  stack: readonly OverlayDescriptor[],
  id: string,
): OverlayDescriptor[] {
  return stack.filter((d) => d.id !== id)
}

export function updateDescriptor(
  stack: readonly OverlayDescriptor[],
  id: string,
  updates: Partial<OverlayDescriptor>,
): OverlayDescriptor[] {
  const next = stack.map((d) => (d.id === id ? { ...d, ...updates, id: d.id } : d))
  return sortStack(next)
}

/**
 * Sort by priority (passive → critical), then openedAt (newer on top).
 * Nested children (parentOverlayId) are lifted above their parent regardless of priority.
 */
export function sortStack(stack: OverlayDescriptor[]): OverlayDescriptor[] {
  let result = [...stack].sort((a, b) => {
    const p = comparePriority(a.priority, b.priority)
    if (p !== 0) return p
    if (a.openedAt !== b.openedAt) return a.openedAt - b.openedAt
    return a.id.localeCompare(b.id)
  })

  let changed = true
  let guard = 0
  while (changed && guard < result.length * result.length + 1) {
    guard += 1
    changed = false
    for (let i = 0; i < result.length; i++) {
      const d = result[i]!
      if (!d.parentOverlayId) continue
      const parentIdx = result.findIndex((x) => x.id === d.parentOverlayId)
      if (parentIdx === -1) continue
      if (i > parentIdx) continue
      result.splice(i, 1)
      const newParentIdx = result.findIndex((x) => x.id === d.parentOverlayId)
      result.splice(newParentIdx + 1, 0, d)
      changed = true
      break
    }
  }
  return result
}

export function getTop(stack: readonly OverlayDescriptor[]): OverlayDescriptor | null {
  return stack.length > 0 ? stack[stack.length - 1]! : null
}

export function isTop(stack: readonly OverlayDescriptor[], id: string): boolean {
  const top = getTop(stack)
  return Boolean(top && top.id === id)
}

/** Descendants (children, grandchildren, …) of parentId. */
export function collectDescendantIds(
  stack: readonly OverlayDescriptor[],
  parentId: string,
): string[] {
  const ids: string[] = []
  const walk = (pid: string) => {
    for (const d of stack) {
      if (d.parentOverlayId === pid) {
        ids.push(d.id)
        walk(d.id)
      }
    }
  }
  walk(parentId)
  return ids
}

/** Close order for a subtree: deepest children first, then parent. */
export function closeOrderForParent(
  stack: readonly OverlayDescriptor[],
  parentId: string,
): string[] {
  const descendants = collectDescendantIds(stack, parentId)
  return [...descendants.reverse(), parentId]
}

/** Reverse stack order for closeAll (top first). */
export function closeAllOrder(stack: readonly OverlayDescriptor[]): string[] {
  return [...stack].reverse().map((d) => d.id)
}
