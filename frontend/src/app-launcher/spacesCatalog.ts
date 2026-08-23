/**
 * Catalogue des espaces métier ELFIS — dérivé du Workspace Registry (SoT).
 * Routes réelles uniquement ; pas de fausses pages.
 */

import {
  buildElfisSpacesFromWorkspaces,
  getWorkspaceById,
  getWorkspaceByProductId,
  getWorkspaceKnownRoutes,
  workspaceToSpaceDefinition,
} from '../workspaces'
import type { SpaceDefinition, SpaceId } from './spaces.types'

/**
 * Mapping entrée :
 * Finance → /dashboard · Commercial → /sales
 * Documents → /platform/documents · 9 espaces roadmap → À venir
 */
export const ELFIS_SPACES: readonly SpaceDefinition[] = buildElfisSpacesFromWorkspaces()

export function getSpaceById(id: SpaceId): SpaceDefinition {
  return workspaceToSpaceDefinition(getWorkspaceById(id))
}

export function getSpaceByProductId(
  productId: string | null | undefined,
): SpaceDefinition | null {
  const workspace = getWorkspaceByProductId(productId)
  if (!workspace) return null
  return workspaceToSpaceDefinition(workspace)
}

/** Routes d’entrée espaces + raccourcis connus (SPA). */
export function getSpaceKnownRoutes(): ReadonlySet<string> {
  return getWorkspaceKnownRoutes()
}
