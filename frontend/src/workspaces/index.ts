export {
  filterWorkspaceLeavesByPermission,
  findActiveWorkspaceGroup,
  findActiveWorkspaceLeaf,
  getVisibleWorkspaceGroups,
  isWorkspaceGroupVisible,
  normalizeWorkspacePath,
  workspaceGroupHasChildren,
  workspacePathMatches,
} from './navHelpers'

export type {
  WorkspaceAccentTokens,
  WorkspaceAvailability,
  WorkspaceConfig,
  WorkspaceId,
  WorkspaceNavActivePolicy,
  WorkspaceNavGroup,
  WorkspaceNavLeaf,
  WorkspaceRegistry,
} from './types'

export {
  WORKSPACE_ACCENTS,
  WORKSPACE_PRIMARY,
  allWorkspaceAccentCssVars,
  workspaceAccentCssDeclarations,
} from './accents'

export { financeWorkspaceConfig } from './financeWorkspaceConfig'
export { commercialWorkspaceConfig } from './commercialWorkspaceConfig'
export { documentsWorkspaceConfig } from './documentsWorkspaceConfig'
export {
  rhWorkspaceConfig,
  analyseWorkspaceConfig,
  supportWorkspaceConfig,
} from './comingSoonWorkspaces'

export {
  WORKSPACE_REGISTRY,
  getWorkspaceById,
  getWorkspaceByProductId,
  getAvailableWorkspaces,
  workspaceToSpaceDefinition,
  buildElfisSpacesFromWorkspaces,
  getWorkspaceKnownRoutes,
  isWorkspaceNavLeafActive,
  assertWorkspaceEngineRegistered,
} from './registry'

/** UI — après le registry pour éviter les cycles d’import (spacesCatalog). */
export { WorkspaceSidebar } from './WorkspaceSidebar'
export type { WorkspaceSidebarProps } from './WorkspaceSidebar'

export { WorkspacePageHeader } from './WorkspacePageHeader'
export type { WorkspacePageHeaderProps } from './WorkspacePageHeader'

export { WorkspaceKpiCard } from './WorkspaceKpiCard'
export type { WorkspaceKpiCardProps } from './WorkspaceKpiCard'
