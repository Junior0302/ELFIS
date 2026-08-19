# 11 — Guide d’intégration

## Importer

```ts
import {
  SmartSearch,
  CustomerPicker,
  SupplierPicker,
  DocumentPicker,
  ProductPicker,
  useSmartSearch,
} from '../platform-search'
```

## Composer Facturation

`FacturationComposerPage` → `ClientStep` utilise `CustomerPicker`.

Mapping vers `WizardSelectedClient` inchangé (customerId / relationId / source).

## Nouveau picker métier

1. Choisir un `SearchScope` existant ou ajouter une source dans `smartSearchSources.ts` branchée sur une **API réelle**.
2. Composer avec `UniversalPicker`.
3. Ne pas appeler un fuzzy maison.

## Command Center

Ne pas réécrire. Ne pas ajouter Cmd+K. Option future : adapters `engineHitToSearchResult` pour affichage unifié — reportée.

## Interdictions

- Pas de 2e Search Engine
- Pas de tables nouvelles sans nécessité
- Pas F1.2 InventoryPilot actif
