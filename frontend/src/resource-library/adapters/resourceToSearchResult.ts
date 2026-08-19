/**
 * Resource → SearchResult (pont ProductPicker / Smart Search).
 */

import type { SearchEntityType, SearchResult } from '../../platform-search/types'
import type { Resource } from '../types'

export function resourceToSearchResult(resource: Resource): SearchResult {
  const type: SearchEntityType =
    resource.kind === 'service' ? 'service' : 'product'
  return {
    type,
    id: resource.id,
    title: resource.name,
    subtitle: `${resource.unitPriceHt.toFixed(2)} € HT · TVA ${resource.vatRate}%`,
    description: resource.description ?? (resource.unit ? `Unité : ${resource.unit}` : undefined),
    status: resource.status,
    route: '/catalogue',
    source: resource.sourceId === 'inventory_pilot' ? 'inventory_pilot' : 'billing_catalog',
    metadata: {
      catalogItemId: resource.catalogItemId ?? (Number(resource.id) || null),
      kind: resource.kind,
      unit: resource.unit,
      unit_price_ht: resource.unitPriceHt,
      vat_rate: resource.vatRate,
      active: resource.status === 'active',
      resourceSourceId: resource.sourceId,
      ...(resource.createdAt ? { created_at: resource.createdAt } : {}),
      ...(resource.updatedAt ? { updated_at: resource.updatedAt } : {}),
    },
    actions: [{ id: 'select', label: 'Sélectionner', kind: 'select' }],
  }
}
