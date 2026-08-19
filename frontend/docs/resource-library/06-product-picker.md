# 06 — ProductPicker ↔ Resource System

## Contrat

ProductPicker (P1.0) reste l’API UI stable.  
`ProductSource` **délègue** à `ResourceSource` via `resourceToSearchResult`.

| ProductSourceId | ResourceSourceId |
|-----------------|------------------|
| `local_catalog` | `local_library` |
| `inventory_pilot` | `inventory_pilot` |

Helper Composer : `catalogResultToLineFields(SearchResult)`.

## Consommateur officiel

`FacturationComposerPage` → `ProductsStep` utilise `ProductPicker` (plus de liste inline).

Création produit inline conservée (même API `createCatalogItem`) + refresh picker.

## Non-régression F1.1

- CustomerPicker inchangé
- Lignes document (`LineEditor`) inchangé
- `catalogResultToLineFields` contract stable
