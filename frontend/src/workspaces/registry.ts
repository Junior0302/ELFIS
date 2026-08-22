/**
 * Registry workspace — source de vérité unique Espaces + future WorkspaceSidebar.
 * Product Registry reste le SoT moteurs ; on compose via engineProductId.
 */

import type { ProductId } from '../design-system/types'
import type { SpaceDefinition } from '../app-launcher/spaces.types'
import { getProductById } from '../design-system/products/registry'
import {
  achatsWorkspaceConfig,
  banqueWorkspaceConfig,
  comptabiliteWorkspaceConfig,
  conformiteWorkspaceConfig,
  facturationWorkspaceConfig,
  logistiqueWorkspaceConfig,
  parametresWorkspaceConfig,
  planningWorkspaceConfig,
  projetsWorkspaceConfig,
  rhWorkspaceConfig,
  rseWorkspaceConfig,
  stockWorkspaceConfig,
} from './comingSoonWorkspaces'
import { commercialWorkspaceConfig } from './commercialWorkspaceConfig'
import { documentsWorkspaceConfig } from './documentsWorkspaceConfig'
import { financeWorkspaceConfig } from './financeWorkspaceConfig'
import type { WorkspaceConfig, WorkspaceId, WorkspaceNavLeaf } from './types'

export const WORKSPACE_REGISTRY: readonly WorkspaceConfig[] = [
  financeWorkspaceConfig,
  commercialWorkspaceConfig,
  documentsWorkspaceConfig,
  achatsWorkspaceConfig,
  stockWorkspaceConfig,
  logistiqueWorkspaceConfig,
  rhWorkspaceConfig,
  planningWorkspaceConfig,
  projetsWorkspaceConfig,
  banqueWorkspaceConfig,
  comptabiliteWorkspaceConfig,
  facturationWorkspaceConfig,
  conformiteWorkspaceConfig,
  rseWorkspaceConfig,
  parametresWorkspaceConfig,
] as const

export function getWorkspaceById(id: WorkspaceId): WorkspaceConfig {
  const found = WORKSPACE_REGISTRY.find((w) => w.id === id)
  if (!found) throw new Error(`Unknown workspace: ${id}`)
  return found
}

export function getWorkspaceByProductId(
  productId: string | null | undefined,
): WorkspaceConfig | null {
  if (!productId) return null
  return WORKSPACE_REGISTRY.find((w) => w.engineProductId === productId) ?? null
}

/** Espaces ouverts (launcher « Espaces métier »). */
export function getAvailableWorkspaces(): WorkspaceConfig[] {
  return WORKSPACE_REGISTRY.filter((w) => w.availability === 'available' && w.rootPath)
}

/** Adapter WorkspaceConfig → SpaceDefinition (launcher hub). */
export function workspaceToSpaceDefinition(workspace: WorkspaceConfig): SpaceDefinition {
  return {
    id: workspace.id,
    title: workspace.label,
    description: workspace.description,
    icon: workspace.icon,
    accent: workspace.accent.primary,
    accentSoft: workspace.accent.soft,
    engineLabel: workspace.engineLabel,
    engineProductId: workspace.engineProductId,
    entryRoute: workspace.rootPath,
    shortcuts: workspace.shortcuts,
    searchAliases: workspace.searchAliases,
    capabilities: workspace.capabilities,
  }
}

/** Catalogue Espaces dérivé du registry (une seule source). */
export function buildElfisSpacesFromWorkspaces(): readonly SpaceDefinition[] {
  return WORKSPACE_REGISTRY.map(workspaceToSpaceDefinition)
}

/** Routes d’entrée + raccourcis connus. */
export function getWorkspaceKnownRoutes(): ReadonlySet<string> {
  const routes = new Set<string>()
  for (const w of WORKSPACE_REGISTRY) {
    if (w.rootPath) routes.add(w.rootPath)
    for (const sc of w.shortcuts) routes.add(sc.to)
    for (const group of w.navigationGroups) {
      routes.add(group.to)
      for (const leaf of group.children) routes.add(leaf.to)
    }
  }
  return routes
}

/**
 * Résout si une feuille doit être active (prépare Phase 3).
 * contextual + même path qu’un sibling primary → jamais actif.
 */
export function isWorkspaceNavLeafActive(
  leaf: WorkspaceNavLeaf,
  pathname: string,
  siblings: readonly WorkspaceNavLeaf[],
): boolean {
  const path = pathname.replace(/\/+$/, '') || '/'
  const target = leaf.to.replace(/\/+$/, '') || '/'
  const policy = leaf.activePolicy ?? 'prefix'

  if (policy === 'contextual') return false

  if (policy === 'exact' || policy === 'primary') {
    if (path !== target) return false
    if (policy === 'primary') return true
    return true
  }

  // prefix
  if (path === target) {
    const hasPrimarySibling = siblings.some(
      (s) =>
        s.id !== leaf.id &&
        s.activePolicy === 'primary' &&
        (s.to.replace(/\/+$/, '') || '/') === target,
    )
    if (hasPrimarySibling) return false
    return true
  }
  if (target === '/') return false
  return path.startsWith(`${target}/`)
}

/** Vérifie que le moteur référencé existe dans Product Registry (si non null). */
export function assertWorkspaceEngineRegistered(workspace: WorkspaceConfig): boolean {
  if (!workspace.engineProductId) return true
  try {
    getProductById(workspace.engineProductId as ProductId)
    return true
  } catch {
    return false
  }
}
