/**
 * Helpers navigation workspace — filtrage permissions + résolution groupe actif.
 */

import type { WorkspaceConfig, WorkspaceNavGroup, WorkspaceNavLeaf } from './types'
import { isWorkspaceNavLeafActive } from './registry'

export function normalizeWorkspacePath(pathname: string): string {
  const trimmed = pathname.replace(/\/+$/, '')
  return trimmed || '/'
}

export function workspacePathMatches(pathname: string, to: string): boolean {
  const path = normalizeWorkspacePath(pathname)
  const target = normalizeWorkspacePath(to)
  if (path === target) return true
  if (target === '/' || target === '/dashboard' || target === '/sales' || target === '/home') {
    return false
  }
  return path.startsWith(`${target}/`)
}

export function filterWorkspaceLeavesByPermission(
  leaves: readonly WorkspaceNavLeaf[],
  can: (permission?: string) => boolean,
): WorkspaceNavLeaf[] {
  return leaves.filter((leaf) => can(leaf.permission))
}

export function isWorkspaceGroupVisible(
  group: WorkspaceNavGroup,
  can: (permission?: string) => boolean,
): boolean {
  if (!can(group.permission)) return false
  if (group.children.length === 0) return true
  return filterWorkspaceLeavesByPermission(group.children, can).length > 0
}

export function getVisibleWorkspaceGroups(
  workspace: WorkspaceConfig,
  can: (permission?: string) => boolean = () => true,
): WorkspaceNavGroup[] {
  return workspace.navigationGroups.filter((g) => isWorkspaceGroupVisible(g, can))
}

export function findActiveWorkspaceGroup(
  pathname: string,
  groups: readonly WorkspaceNavGroup[],
  /** Sur égalité de score, retourne true pour préférer le candidat. */
  preferCandidate?: (
    best: WorkspaceNavGroup | undefined,
    candidate: WorkspaceNavGroup,
  ) => boolean,
): WorkspaceNavGroup | undefined {
  const path = normalizeWorkspacePath(pathname)
  let best: WorkspaceNavGroup | undefined
  let bestScore = -1

  for (const group of groups) {
    const candidates = [group.to, ...group.children.map((c) => c.to)]
    for (const to of candidates) {
      if (!workspacePathMatches(path, to)) continue
      const score = normalizeWorkspacePath(to).length
      if (score > bestScore) {
        bestScore = score
        best = group
      } else if (score === bestScore) {
        if (preferCandidate?.(best, group)) {
          best = group
        } else if (
          !preferCandidate &&
          group.children.length > (best?.children.length ?? 0)
        ) {
          /* Préférer le groupe avec sous-menus (ex. Documents vs Tableau de bord même path). */
          best = group
        }
      }
    }
  }
  return best
}

export function findActiveWorkspaceLeaf(
  pathname: string,
  group: WorkspaceNavGroup,
): WorkspaceNavLeaf | undefined {
  const siblings = group.children
  return siblings.find((leaf) => isWorkspaceNavLeafActive(leaf, pathname, siblings))
}

export function workspaceGroupHasChildren(group: WorkspaceNavGroup | undefined): boolean {
  return Boolean(group && group.children.length > 0)
}
