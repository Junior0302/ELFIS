# 04 — Stratégie catalogue

## ComptaPilot = catalogue local par défaut

API : `GET/POST /billing/catalog` via `api.listCatalog` / `createCatalogItem`.

Type : `CatalogItem` (prix HT, TVA, actif).

## Abstraction source

```ts
catalogSource: 'local' | 'inventory'
```

F1.0–F1.1 : **seul `local` est branché**. `isInventoryCatalogAvailable()` → `false`.

**F1.2** : Smart Library / `LocalLibrarySource` = source officielle ; ProductPicker consomme Resource System.
Voir [`../resource-library/`](../resource-library/README.md).

## UX produits (wizard)

- ProductPicker (Smart Search scope products) sur catalogue local réel
- Favoris / récents / plus vendus : **off** (pas de source)
- Créer produit → API catalogue locale
- Lien vers `/catalogue` (Smart Library)

## Ne pas faire

- Dupliquer un second catalogue Inventory
- Modifier InventoryPilot
- Inventer des produits de démo
- Commencer F1.4
