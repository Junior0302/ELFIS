/**
 * ELFIS Resource System / Smart Library V1 — API publique.
 */

export type {
  Resource,
  ResourceKind,
  ResourceStatus,
  ResourceSourceId,
  ResourceQuery,
  ResourceListResult,
  ResourceCreateInput,
  ResourceUpdateInput,
  ResourceActionId,
  ResourceActionDef,
  LibraryNavSection,
  ResourceSort,
  LibraryMetaProvider,
} from './types'

export type { ResourceSource } from './sources/resourceSource'
export {
  resolveResourceSource,
  getActiveResourceSource,
  localLibrarySource,
  inventoryPilotResourceSource,
} from './sources/resolveResourceSource'
export { duplicateLocalResource } from './sources/localLibrarySource'
export { catalogItemToResource, resourceKindToCatalogKind } from './adapters/catalogToResource'
export { resourceToSearchResult } from './adapters/resourceToSearchResult'
export {
  DISABLED_FAVORITES,
  DISABLED_RECENTS,
  DISABLED_MOST_USED,
  LIBRARY_META_PROVIDERS,
} from './contracts/libraryMeta'
export { getResourceActions } from './actions'
export { useResourceLibrary } from './hooks/useResourceLibrary'
export type { SmartLibraryFilters } from './hooks/useResourceLibrary'

export { ResourceCard } from './ui/ResourceCard'
export { SmartLibraryNav } from './ui/SmartLibraryNav'
export { SmartFilters } from './ui/SmartFilters'
export { LibraryEmptyState } from './ui/LibraryEmptyState'
export { ResourceCreateForm } from './ui/ResourceCreateForm'
export { ImportPlaceholder } from './ui/ImportPlaceholder'
export { default as SmartLibraryPage } from './ui/SmartLibraryPage'
