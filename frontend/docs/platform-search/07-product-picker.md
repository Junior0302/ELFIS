# 07 — Product picker

## Contrat ProductSource (aligné Resource System F1.2)

```ts
type ProductSource = {
  id: 'local_catalog' | 'inventory_pilot'
  label: string
  available: boolean
  resourceSourceId: 'local_library' | 'inventory_pilot'
  search: (q) => Promise<SearchResult[]>
}
```

| Source | V1 |
|--------|-----|
| `localCatalogProductSource` | **disponible** — délègue à `LocalLibrarySource` |
| `inventoryPilotProductSource` | `available: false` — stub Inventory |

Empty honnête si catalogue vide. Favoris / top vendus **off** (pas de source).

Interface picker **identique** quelle que soit la source active.

Premier consommateur officiel Smart Library : Document Composer (`ProductsStep`).  
Voir [`../resource-library/06-product-picker.md`](../resource-library/06-product-picker.md).
