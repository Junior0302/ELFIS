/**
 * ELFIS Platform Smart Search & Universal Pickers V1
 * Couche UX + contrats — Search Engine V1 reste la source fuzzy technique.
 */

export type {
  SearchAction,
  SearchEntityType,
  SearchFilter,
  SearchGroup,
  SearchPermission,
  SearchQuery,
  SearchResult,
  SearchScope,
  SmartSearchResponse,
  SmartSearchStatus,
  RecentsProvider,
  FavoritesProvider,
} from './types'

export { mapEngineResourceType, groupResultsByType, V1_ENTITY_TYPES_WITH_SOURCE } from './mapResourceType'
export { handleListKeyboard, GLOBAL_SHORTCUT_OWNER } from './keyboard'
export { useDebouncedValue } from './hooks/useDebouncedValue'
export { useSmartSearch } from './hooks/useSmartSearch'
export type { UseSmartSearchOptions } from './hooks/useSmartSearch'

export { SmartSearch } from './ui/SmartSearch'
export type { SmartSearchProps } from './ui/SmartSearch'

export {
  runSmartSearch,
  searchViaEngine,
  searchRelations,
  searchCustomers,
  searchBillingDocuments,
  searchProducts,
  DISABLED_RECENTS,
  DISABLED_FAVORITES,
} from './sources/smartSearchSources'

export {
  localCatalogProductSource,
  inventoryPilotProductSource,
  resolveProductSource,
} from './sources/productSource'
export type { ProductSource, ProductSourceId, ProductSourceQuery } from './sources/productSource'

export { UniversalPicker } from './pickers/UniversalPicker'
export type { UniversalPickerProps, UniversalPickerCreateAction } from './pickers/UniversalPicker'
export { RelationPicker } from './pickers/RelationPicker'
export type { RelationPickerProps } from './pickers/RelationPicker'
export { CustomerPicker, searchResultToCustomerSelection } from './pickers/CustomerPicker'
export type { CustomerPickerProps, CustomerPickerSelection } from './pickers/CustomerPicker'
export { SupplierPicker } from './pickers/SupplierPicker'
export type { SupplierPickerProps } from './pickers/SupplierPicker'
export { DocumentPicker } from './pickers/DocumentPicker'
export type { DocumentPickerProps } from './pickers/DocumentPicker'
export { ProductPicker, catalogResultToLineFields } from './pickers/ProductPicker'
export type { ProductPickerProps } from './pickers/ProductPicker'

export { engineHitToSearchResult } from './adapters/searchEngineAdapter'
export { sharedRelationToSearchResult, customerRecordToSearchResult } from './adapters/relationAdapter'
export { catalogItemToSearchResult, salesDocToSearchResult } from './adapters/documentAdapter'
