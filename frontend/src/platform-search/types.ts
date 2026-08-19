/**
 * ELFIS Platform Smart Search V1 — contrats génériques (pas Compta-spécifiques).
 * Couche UX / normalisation ; le fuzzy reste Search Engine V1 côté backend.
 */

/** Types V1 uniquement s’il existe une source réelle (extensible sans fake). */
export type SearchEntityType =
  | 'relation'
  | 'customer'
  | 'supplier'
  | 'document'
  | 'invoice'
  | 'quote'
  | 'credit_note'
  | 'product'
  | 'service'
  | 'accounting_entry'
  | 'organization'
  | 'user'
  | 'vault_document'
  | 'unknown'

export type SearchScope =
  | 'global'
  | 'relations'
  | 'customers'
  | 'suppliers'
  | 'documents'
  | 'products'
  | 'accounting'

export type SearchPermission = {
  /** Feature / permission key (ex. SEARCH_GLOBAL, invoice.read) */
  key: string
  granted: boolean
}

export type SearchAction = {
  id: string
  label: string
  kind: 'select' | 'navigate' | 'create' | 'open' | 'custom'
  href?: string
  disabled?: boolean
}

export type SearchFilter = {
  key: string
  value: string | number | boolean | null
}

export type SearchQuery = {
  q: string
  scope?: SearchScope
  types?: SearchEntityType[]
  filters?: SearchFilter[]
  page?: number
  pageSize?: number
  /** Opaque org / tenant — toujours passé via auth, jamais inventé */
  organizationId?: number | null
}

export type SearchResult = {
  type: SearchEntityType
  id: string
  title: string
  subtitle?: string
  description?: string
  icon?: string
  metadata?: Record<string, unknown>
  status?: string | null
  route?: string | null
  source: string
  permissions?: SearchPermission[]
  actions?: SearchAction[]
  /** Score Search Engine V1 si applicable */
  score?: number
}

export type SearchGroup = {
  id: string
  label: string
  type?: SearchEntityType | 'mixed'
  items: SearchResult[]
}

export type SmartSearchStatus =
  | 'idle'
  | 'typing'
  | 'loading'
  | 'ready'
  | 'empty'
  | 'error'
  | 'offline'
  | 'partial'

export type SmartSearchResponse = {
  groups: SearchGroup[]
  items: SearchResult[]
  total: number
  page: number
  pageSize: number
  status: SmartSearchStatus
  partial?: boolean
  errorMessage?: string | null
  executionTimeMs?: number
  /** Identifie la source technique (search_engine_v1, shared_relations, …) */
  engine?: string
}

/** Contrat récents / favoris — désactivé si aucune source métier réelle. */
export type RecentsProvider = {
  enabled: boolean
  list: (limit?: number) => Promise<SearchResult[]>
  remember?: (item: SearchResult) => Promise<void>
}

export type FavoritesProvider = {
  enabled: boolean
  list: () => Promise<SearchResult[]>
  toggle?: (item: SearchResult) => Promise<void>
}
