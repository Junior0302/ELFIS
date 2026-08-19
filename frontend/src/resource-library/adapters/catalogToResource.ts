/**
 * CatalogItem (billing) → Resource (Resource System).
 */

import type { CatalogItem } from '../../api'
import type { Resource, ResourceKind } from '../types'

export function catalogKindToResourceKind(kind: string): ResourceKind {
  if (kind === 'service') return 'service'
  if (kind === 'pack') return 'pack'
  return 'product'
}

export function resourceKindToCatalogKind(kind: ResourceKind): string {
  if (kind === 'service') return 'service'
  if (kind === 'pack') return 'pack'
  return 'produit'
}

export function catalogItemToResource(item: CatalogItem): Resource {
  return {
    id: String(item.id),
    sourceId: 'local_library',
    kind: catalogKindToResourceKind(item.kind),
    name: item.name,
    unit: item.unit,
    unitPriceHt: item.unit_price_ht,
    vatRate: item.vat_rate,
    status: item.active ? 'active' : 'inactive',
    catalogItemId: item.id,
    createdAt: item.created_at,
    updatedAt: item.updated_at,
    lastUsedAt: null,
    category: null,
    metadata: {
      kindRaw: item.kind,
    },
  }
}
