# 01 — Runtime audit (F1.2)

## Catalogue avant F1.2

| Élément | État |
|---------|------|
| Route `/catalogue` | `CataloguePage` CRUD list/form basique |
| API | `GET/POST/PATCH/DELETE /billing/catalog` |
| Modèle | `CatalogItem` (`produit` \| `service`) — pas de packs |
| Permissions | `invoice.read` / `invoice.create` |
| Import CSV catalogue | Absent |
| Favoris / récents / plus utilisés | Pas d’API — empty / providers OFF |
| ProductPicker | Prêt P1.0, **non branché** au Composer |
| ProductsStep Composer | Liste inline `listCatalog` |
| InventoryPilot | Stub `available: false` |
| ResourceSource / Smart Library | Absents |

## Décisions de réutilisation

| Réutiliser | Ne pas inventer |
|-----------|-----------------|
| API billing catalog + `CatalogItem` | Favoris / récents / top (localStorage métier interdit) |
| `ProductSource` / ProductPicker / Smart Search scope `products` | Packs sans modèle backend |
| Permissions `invoice.*` | Permission `catalog.*` dédiée |
| Redirects `/facturation/catalogue`, `/catalog`, `/sales/catalog` | Second catalogue Inventory |
| Empty states honnêtes (P1.0) | Import CSV implémenté |

## Alignement ProductSource → Resource System

- `LocalLibrarySource` = owner données locales
- `ProductSource` = adaptateur SearchResult pour pickers (rétrocompat P1.0)
- UI ne référence jamais `api.listCatalog` hors adapters / sources

## Nav F1.0

- Nav principale : `/catalogue` (label Catalogue)
- Espaces Facturation : `/facturation/catalogue` → redirect `/catalogue`
- Conservé tel quel (Smart Library remplace le contenu de la page)
