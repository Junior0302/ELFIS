/**
 * LocalLibrarySource — catalogue billing ComptaPilot (source réelle V1).
 */

import { api, type CatalogItem } from '../../api'
import { catalogItemToResource, resourceKindToCatalogKind } from '../adapters/catalogToResource'
import type {
  Resource,
  ResourceCreateInput,
  ResourceKind,
  ResourceListResult,
  ResourceQuery,
  ResourceSort,
  ResourceUpdateInput,
} from '../types'
import type { ResourceSource } from './resourceSource'

function applyFilters(items: Resource[], query: ResourceQuery): Resource[] {
  let list = items
  const q = (query.q ?? '').trim().toLowerCase()
  if (q) {
    list = list.filter(
      (r) =>
        r.name.toLowerCase().includes(q) ||
        (r.description ?? '').toLowerCase().includes(q) ||
        r.unit.toLowerCase().includes(q),
    )
  }
  if (query.kinds?.length) {
    const allowed = new Set(query.kinds)
    list = list.filter((r) => allowed.has(r.kind))
  }
  if (query.status && query.status !== 'any') {
    list = list.filter((r) => r.status === query.status)
  }
  if (query.vatRates?.length) {
    const rates = new Set(query.vatRates)
    list = list.filter((r) => rates.has(r.vatRate))
  }
  if (query.priceMin != null) {
    list = list.filter((r) => r.unitPriceHt >= query.priceMin!)
  }
  if (query.priceMax != null) {
    list = list.filter((r) => r.unitPriceHt <= query.priceMax!)
  }
  if (query.category) {
    list = list.filter((r) => (r.category ?? '') === query.category)
  }
  return sortResources(list, query.sort ?? 'name_asc')
}

function sortResources(items: Resource[], sort: ResourceSort): Resource[] {
  const copy = [...items]
  copy.sort((a, b) => {
    switch (sort) {
      case 'name_desc':
        return b.name.localeCompare(a.name, 'fr')
      case 'price_asc':
        return a.unitPriceHt - b.unitPriceHt
      case 'price_desc':
        return b.unitPriceHt - a.unitPriceHt
      case 'updated_desc': {
        const ta = a.updatedAt ?? a.createdAt ?? ''
        const tb = b.updatedAt ?? b.createdAt ?? ''
        return tb.localeCompare(ta)
      }
      case 'name_asc':
      default:
        return a.name.localeCompare(b.name, 'fr')
    }
  })
  return copy
}

function paginate(items: Resource[], page: number, pageSize: number): ResourceListResult {
  const start = (page - 1) * pageSize
  const slice = items.slice(start, start + pageSize)
  return {
    items: slice,
    total: items.length,
    page,
    pageSize,
    hasMore: start + pageSize < items.length,
  }
}

async function fetchAll(
  token: string,
  orgId: number | null | undefined,
  activeOnly: boolean,
  signal?: AbortSignal,
): Promise<Resource[]> {
  if (signal?.aborted) throw new DOMException('Aborted', 'AbortError')
  const res = await api.listCatalog(token, orgId, activeOnly)
  if (signal?.aborted) throw new DOMException('Aborted', 'AbortError')
  return (res.items ?? []).map(catalogItemToResource)
}

async function listLocal(query: ResourceQuery): Promise<ResourceListResult> {
  const page = query.page ?? 1
  const pageSize = query.pageSize ?? 40
  const activeOnly = query.activeOnly ?? false
  const all = await fetchAll(query.token, query.orgId, activeOnly, query.signal)
  return paginate(applyFilters(all, query), page, pageSize)
}

export const localLibrarySource: ResourceSource = {
  id: 'local_library',
  label: 'Bibliothèque locale',
  available: true,
  capabilities: {
    list: true,
    search: true,
    create: true,
    update: true,
    delete: true,
    duplicate: true,
    history: false,
    favorites: false,
    recents: false,
    mostUsed: false,
    import: false,
    packs: false,
  },
  list: listLocal,
  async search(query) {
    const result = await listLocal({
      ...query,
      page: 1,
      pageSize: query.pageSize ?? 40,
    })
    return result.items
  },
  async get(id, token, orgId) {
    const all = await fetchAll(token, orgId, false)
    return all.find((r) => r.id === id) ?? null
  },
  async create(input: ResourceCreateInput, token, orgId) {
    if (input.kind === 'pack') {
      throw new Error('Les packs ne sont pas supportés par la bibliothèque locale V1')
    }
    const created = await api.createCatalogItem(
      {
        name: input.name.trim(),
        kind: resourceKindToCatalogKind(input.kind),
        unit: input.unit ?? 'unité',
        unit_price_ht: input.unitPriceHt,
        vat_rate: input.vatRate,
        active: input.active ?? true,
      },
      token,
      orgId,
    )
    return catalogItemToResource(created)
  },
  async update(id, input: ResourceUpdateInput, token, orgId) {
    if (input.kind === 'pack') {
      throw new Error('Les packs ne sont pas supportés par la bibliothèque locale V1')
    }
    const payload: Partial<{
      name: string
      kind: string
      unit: string
      unit_price_ht: number
      vat_rate: number
      active: boolean
    }> = {}
    if (input.name != null) payload.name = input.name.trim()
    if (input.kind != null) payload.kind = resourceKindToCatalogKind(input.kind)
    if (input.unit != null) payload.unit = input.unit
    if (input.unitPriceHt != null) payload.unit_price_ht = input.unitPriceHt
    if (input.vatRate != null) payload.vat_rate = input.vatRate
    if (input.active != null) payload.active = input.active
    const updated = await api.updateCatalogItem(Number(id), payload, token, orgId)
    return catalogItemToResource(updated)
  },
  async delete(id, token, orgId) {
    await api.deleteCatalogItem(Number(id), token, orgId)
  },
}

/** Duplique via create — action supportée côté LocalLibrary. */
export async function duplicateLocalResource(
  resource: Resource,
  token: string,
  orgId?: number | null,
): Promise<Resource> {
  const kind: ResourceKind = resource.kind === 'pack' ? 'product' : resource.kind
  return localLibrarySource.create!(
    {
      name: `${resource.name} (copie)`,
      kind,
      unit: resource.unit,
      unitPriceHt: resource.unitPriceHt,
      vatRate: resource.vatRate,
      active: resource.status === 'active',
    },
    token,
    orgId,
  )
}

/** Helper tests / debug — mappe un CatalogItem brut. */
export function mapCatalogItems(items: CatalogItem[]): Resource[] {
  return items.map(catalogItemToResource)
}
