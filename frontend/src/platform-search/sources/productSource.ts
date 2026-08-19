/**
 * ProductSource P1.0 — aligné sur Resource System.
 * Conserve l’API SearchResult pour ProductPicker / Smart Search.
 */

import { resourceToSearchResult } from '../../resource-library/adapters/resourceToSearchResult'
import {
  inventoryPilotResourceSource,
  localLibrarySource,
  resolveResourceSource,
} from '../../resource-library/sources/resolveResourceSource'
import type { ResourceSourceId as LibSourceId } from '../../resource-library/types'
import type { SearchResult } from '../types'

export type ProductSourceId = 'local_catalog' | 'inventory_pilot'

export type ProductSourceQuery = {
  q: string
  token: string
  orgId?: number | null
  activeOnly?: boolean
  limit?: number
}

export type ProductSource = {
  id: ProductSourceId
  label: string
  available: boolean
  search: (query: ProductSourceQuery) => Promise<SearchResult[]>
  /** Source Resource System sous-jacente (opaque pour UI). */
  resourceSourceId: LibSourceId
}

function wrapResourceAsProduct(
  prefer: LibSourceId,
  productId: ProductSourceId,
  labelOverride?: string,
): ProductSource {
  const source = resolveResourceSource(prefer)
  return {
    id: productId,
    label: labelOverride ?? source.label,
    available: source.available,
    resourceSourceId: source.id,
    async search({ q, token, orgId, activeOnly = true, limit = 40 }) {
      if (!source.available) return []
      const searchFn = source.search ?? (async (query) => (await source.list(query)).items)
      const items = await searchFn({
        q,
        token,
        orgId,
        activeOnly,
        page: 1,
        pageSize: limit,
      })
      return items.map(resourceToSearchResult)
    },
  }
}

/** Catalogue local ComptaPilot — source réelle V1 (via LocalLibrarySource). */
export const localCatalogProductSource: ProductSource = wrapResourceAsProduct(
  'local_library',
  'local_catalog',
  'Catalogue local',
)

/**
 * Stub InventoryPilot — même interface ProductSource, indisponible.
 * Branchement futur = activer inventoryPilotResourceSource.available.
 */
export const inventoryPilotProductSource: ProductSource = {
  id: 'inventory_pilot',
  label: inventoryPilotResourceSource.label,
  available: inventoryPilotResourceSource.available,
  resourceSourceId: 'inventory_pilot',
  async search() {
    return []
  },
}

export function resolveProductSource(prefer: ProductSourceId = 'local_catalog'): ProductSource {
  if (prefer === 'inventory_pilot' && inventoryPilotProductSource.available) {
    return inventoryPilotProductSource
  }
  return localCatalogProductSource
}

/** Pont explicite Resource System ↔ ProductPicker. */
export function productSourceFromResource(prefer: LibSourceId = 'local_library'): ProductSource {
  if (prefer === 'inventory_pilot') {
    return resolveProductSource('inventory_pilot')
  }
  return resolveProductSource('local_catalog')
}

export { localLibrarySource, inventoryPilotResourceSource }
