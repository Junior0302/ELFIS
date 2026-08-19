# 02 — Resource model

```ts
type ResourceKind = 'product' | 'service' | 'pack'
type ResourceStatus = 'active' | 'inactive'
type ResourceSourceId = 'local_library' | 'inventory_pilot'

type Resource = {
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
  catalogItemId?: number | null
  lastUsedAt?: string | null
  createdAt?: string
  updatedAt?: string
  metadata?: Record<string, unknown>
}
```

## Mapping Local Library

| CatalogItem | Resource |
|-------------|----------|
| `id` | `id` (string) + `catalogItemId` |
| `kind: produit\|service` | `product\|service` |
| `unit_price_ht` | `unitPriceHt` |
| `vat_rate` | `vatRate` |
| `active` | `status` |
| — | `lastUsedAt: null` (non exposé) |
| — | `category: null` (non exposé) |
| — | `pack` non supporté V1 |

Fichier : `frontend/src/resource-library/types.ts` · adapter `catalogToResource.ts`
