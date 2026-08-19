/**
 * ELFIS Resource System — modèles transversaux (Smart Library V1).
 * Source concrète opaque hors adapters.
 */

export type ResourceKind = 'product' | 'service' | 'pack'

export type ResourceStatus = 'active' | 'inactive'

export type ResourceSourceId = 'local_library' | 'inventory_pilot'

export type LibraryNavSection =
  | 'all'
  | 'products'
  | 'services'
  | 'packs'
  | 'favorites'
  | 'recents'
  | 'most_used'

export type ResourceSort =
  | 'name_asc'
  | 'name_desc'
  | 'price_asc'
  | 'price_desc'
  | 'updated_desc'

export type Resource = {
  id: string
  sourceId: ResourceSourceId
  kind: ResourceKind
  name: string
  description?: string
  unit: string
  unitPriceHt: number
  vatRate: number
  status: ResourceStatus
  category?: string | null
  /** Identifiant catalogue billing (local) — opaque pour UI. */
  catalogItemId?: number | null
  lastUsedAt?: string | null
  createdAt?: string
  updatedAt?: string
  metadata?: Record<string, unknown>
}

export type ResourceQuery = {
  q?: string
  token: string
  orgId?: number | null
  kinds?: ResourceKind[]
  status?: ResourceStatus | 'any'
  vatRates?: number[]
  priceMin?: number | null
  priceMax?: number | null
  category?: string | null
  sort?: ResourceSort
  activeOnly?: boolean
  page?: number
  pageSize?: number
  signal?: AbortSignal
}

export type ResourceListResult = {
  items: Resource[]
  total: number
  page: number
  pageSize: number
  hasMore: boolean
}

export type ResourceCreateInput = {
  name: string
  kind: ResourceKind
  unit?: string
  unitPriceHt: number
  vatRate: number
  active?: boolean
  description?: string
}

export type ResourceUpdateInput = Partial<ResourceCreateInput> & {
  active?: boolean
}

export type ResourceActionId =
  | 'add'
  | 'edit'
  | 'duplicate'
  | 'view'
  | 'history'
  | 'delete'

export type ResourceActionDef = {
  id: ResourceActionId
  label: string
  /** true = API réelle branchée */
  available: boolean
  disabledReason?: string
}

/** Contrat favoris / récents / plus utilisés — désactivé sans source réelle. */
export type LibraryMetaProvider = {
  id: 'favorites' | 'recents' | 'most_used'
  label: string
  enabled: boolean
  list: () => Promise<Resource[]>
  reasonDisabled?: string
}
