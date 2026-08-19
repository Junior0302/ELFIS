# 03 — ResourceSource

## Contrat

```ts
type ResourceSource = {
  id: ResourceSourceId
  label: string
  available: boolean
  capabilities: { list, search, create, update, delete, duplicate, history, favorites, recents, mostUsed, import, packs }
  list(query): Promise<ResourceListResult>
  search?(query): Promise<Resource[]>
  create? / update? / delete? / get?
}
```

## Résolution

`resolveResourceSource(prefer)` :

1. Si `inventory_pilot` **et** `available` → InventoryPilot
2. Sinon → `localLibrarySource`

Les pages / pickers appellent `getActiveResourceSource()` ou `resolveProductSource()` — **jamais** l’implémentation concrète hors adapters.

## Instances V1

| Source | available | Rôle |
|--------|-----------|------|
| `localLibrarySource` | `true` | Catalogue billing |
| `inventoryPilotResourceSource` | `false` | Stub prêt |

Fichiers : `sources/resourceSource.ts`, `localLibrarySource.ts`, `inventoryPilotSource.ts`, `resolveResourceSource.ts`
