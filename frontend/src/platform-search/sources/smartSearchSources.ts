/**
 * Sources Smart Search — branchées sur APIs existantes uniquement.
 * Pas de second Search Engine.
 */

import { api } from '../../api'
import { engineHitToSearchResult } from '../adapters/searchEngineAdapter'
import {
  customerRecordToSearchResult,
  sharedRelationToSearchResult,
} from '../adapters/relationAdapter'
import { salesDocToSearchResult } from '../adapters/documentAdapter'
import { groupResultsByType } from '../mapResourceType'
import type {
  FavoritesProvider,
  RecentsProvider,
  SearchQuery,
  SearchResult,
  SmartSearchResponse,
} from '../types'
import { resolveProductSource } from './productSource'

export const DISABLED_RECENTS: RecentsProvider = {
  enabled: false,
  async list() {
    return []
  },
}

export const DISABLED_FAVORITES: FavoritesProvider = {
  enabled: false,
  async list() {
    return []
  },
}

export type SmartSearchSourceOptions = {
  token: string
  orgId?: number | null
  signal?: AbortSignal
}

function assertNotAborted(signal?: AbortSignal) {
  if (signal?.aborted) {
    const err = new Error('aborted')
    err.name = 'AbortError'
    throw err
  }
}

/** Recherche globale via Search Engine V1 (fuzzy backend). */
export async function searchViaEngine(
  query: SearchQuery,
  opts: SmartSearchSourceOptions,
): Promise<SmartSearchResponse> {
  assertNotAborted(opts.signal)
  const q = query.q.trim()
  const page = query.page ?? 1
  const pageSize = query.pageSize ?? 20

  const resourceType =
    query.types?.length === 1
      ? mapSmartTypeToEngine(query.types[0])
      : undefined

  const res = await api.searchElfis(
    {
      q,
      page,
      page_size: pageSize,
      sort: 'relevance',
      resource_type: resourceType,
    },
    opts.token,
    opts.orgId,
  )
  assertNotAborted(opts.signal)

  let items = (res.items ?? []).map(engineHitToSearchResult)
  if (query.types?.length) {
    const allowed = new Set(query.types)
    items = items.filter((i) => allowed.has(i.type) || i.type === 'unknown')
  }

  return {
    groups: groupResultsByType(items),
    items,
    total: res.total ?? items.length,
    page: res.page ?? page,
    pageSize: res.page_size ?? pageSize,
    status: items.length ? 'ready' : 'empty',
    executionTimeMs: res.execution_time_ms,
    engine: 'search_engine_v1',
  }
}

function mapSmartTypeToEngine(type: string): string | undefined {
  switch (type) {
    case 'customer':
      return 'customer'
    case 'supplier':
      return 'supplier'
    case 'accounting_entry':
      return 'accounting_entry'
    case 'vault_document':
      return 'vault_document'
    case 'quote':
      return 'sales_proposal'
    default:
      return undefined
  }
}

/** Relations — SharedRelation API (sélection métier). */
export async function searchRelations(
  query: SearchQuery,
  opts: SmartSearchSourceOptions & { role?: string },
): Promise<SmartSearchResponse> {
  assertNotAborted(opts.signal)
  const q = query.q.trim()
  const page = query.page ?? 1
  const pageSize = query.pageSize ?? 20
  const role = opts.role

  const res = q
    ? await api.searchSharedRelations(opts.token, opts.orgId, q, page, pageSize)
    : await api.listSharedRelations(opts.token, opts.orgId, {
        role,
        page,
        page_size: pageSize,
      })
  assertNotAborted(opts.signal)

  let items = (res.items ?? []).map((r) =>
    sharedRelationToSearchResult(
      r,
      role === 'customer' ? 'customer' : role === 'supplier' ? 'supplier' : undefined,
    ),
  )

  if (role === 'customer') {
    items = items.filter(
      (i) =>
        (i.metadata?.roles as string[] | undefined)?.includes('customer') ||
        i.metadata?.source_system === 'customer' ||
        i.type === 'customer',
    )
  } else if (role === 'supplier') {
    items = items.filter(
      (i) =>
        (i.metadata?.roles as string[] | undefined)?.includes('supplier') ||
        i.type === 'supplier',
    )
  }

  return {
    groups: groupResultsByType(items),
    items,
    total: res.total ?? items.length,
    page: res.page ?? page,
    pageSize: res.page_size ?? pageSize,
    status: items.length ? 'ready' : 'empty',
    engine: 'shared_relations',
  }
}

/** Clients : SharedRelation + fallback billing customers (zéro régression Composer). */
export async function searchCustomers(
  query: SearchQuery,
  opts: SmartSearchSourceOptions,
): Promise<SmartSearchResponse> {
  assertNotAborted(opts.signal)
  const q = query.q.trim()
  const pageSize = query.pageSize ?? 20

  const [relSettled, custSettled] = await Promise.allSettled([
    q
      ? api.searchSharedRelations(opts.token, opts.orgId, q, 1, pageSize)
      : api.listSharedRelations(opts.token, opts.orgId, {
          role: 'customer',
          page_size: pageSize,
        }),
    api.listCustomers(opts.token, opts.orgId, q || undefined),
  ])
  assertNotAborted(opts.signal)

  const items: SearchResult[] = []
  let partial = false

  if (relSettled.status === 'fulfilled') {
    const raw = relSettled.value.items ?? []
    const filtered = q
      ? raw.filter((r) => r.roles.includes('customer') || r.source_system === 'customer')
      : raw
    items.push(...filtered.map((r) => sharedRelationToSearchResult(r, 'customer')))
  } else {
    partial = true
  }

  if (custSettled.status === 'fulfilled') {
    items.push(...(custSettled.value.customers ?? []).map(customerRecordToSearchResult))
  } else {
    partial = true
  }

  if (relSettled.status === 'rejected' && custSettled.status === 'rejected') {
    const msg =
      relSettled.reason instanceof Error
        ? relSettled.reason.message
        : 'Recherche clients indisponible'
    return {
      groups: [],
      items: [],
      total: 0,
      page: 1,
      pageSize,
      status: 'error',
      errorMessage: msg,
      engine: 'customers_dual',
    }
  }

  return {
    groups: groupResultsByType(items),
    items,
    total: items.length,
    page: 1,
    pageSize,
    status: items.length ? (partial ? 'partial' : 'ready') : 'empty',
    partial,
    engine: 'customers_dual',
  }
}

/** Documents commerciaux via billingOverview (source réelle ; pas d’index invoice dédié). */
export async function searchBillingDocuments(
  query: SearchQuery,
  opts: SmartSearchSourceOptions & { docType?: string },
): Promise<SmartSearchResponse> {
  assertNotAborted(opts.signal)
  const q = query.q.trim()
  const pageSize = query.pageSize ?? 30

  const res = await api.billingOverview(opts.token, opts.orgId, {
    q: q || undefined,
    doc_type: opts.docType,
  })
  assertNotAborted(opts.signal)

  let docs = res.documents ?? []
  if (query.types?.length) {
    const allowed = new Set(query.types)
    docs = docs.filter((d) => {
      const mapped = salesDocToSearchResult(d)
      return allowed.has(mapped.type)
    })
  }

  const items = docs.slice(0, pageSize).map(salesDocToSearchResult)
  return {
    groups: groupResultsByType(items),
    items,
    total: items.length,
    page: 1,
    pageSize,
    status: items.length ? 'ready' : 'empty',
    engine: 'billing_sales_documents',
  }
}

export async function searchProducts(
  query: SearchQuery,
  opts: SmartSearchSourceOptions,
): Promise<SmartSearchResponse> {
  assertNotAborted(opts.signal)
  const source = resolveProductSource('local_catalog')
  if (!source.available) {
    return {
      groups: [],
      items: [],
      total: 0,
      page: 1,
      pageSize: query.pageSize ?? 40,
      status: 'empty',
      errorMessage: 'Aucune source catalogue disponible',
      engine: source.id,
    }
  }
  const items = await source.search({
    q: query.q,
    token: opts.token,
    orgId: opts.orgId,
    limit: query.pageSize ?? 40,
  })
  assertNotAborted(opts.signal)
  return {
    groups: groupResultsByType(items),
    items,
    total: items.length,
    page: 1,
    pageSize: query.pageSize ?? 40,
    status: items.length ? 'ready' : 'empty',
    engine: source.id,
  }
}

/** Routeur scope → source appropriée (jamais un nouveau moteur fuzzy). */
export async function runSmartSearch(
  query: SearchQuery,
  opts: SmartSearchSourceOptions,
): Promise<SmartSearchResponse> {
  const scope = query.scope ?? 'global'
  switch (scope) {
    case 'relations':
      return searchRelations(query, opts)
    case 'customers':
      return searchCustomers(query, opts)
    case 'suppliers':
      return searchRelations(query, { ...opts, role: 'supplier' })
    case 'documents':
      return searchBillingDocuments(query, opts)
    case 'products':
      return searchProducts(query, opts)
    case 'accounting':
      return searchViaEngine(
        { ...query, types: query.types ?? ['accounting_entry'] },
        opts,
      )
    case 'global':
    default:
      return searchViaEngine(query, opts)
  }
}
