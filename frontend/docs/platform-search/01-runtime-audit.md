# 01 — Runtime audit (P1.0)

**Décision globale : réutiliser avant reconstruire.** Search Engine V1 + Command Center ⌘K sont la source de vérité ; les sélecteurs facturation étaient ad hoc → extraits vers Universal Pickers.

## Matrice

| Surface | Composant | API | Source | Recherche | Sélection | Réutilisable | Duplication | Décision |
|---------|-----------|-----|--------|-----------|-----------|--------------|-------------|----------|
| Search Engine V1 | `backend/app/search/*`, `api.searchElfis` | `GET /api/search` | Postgres FTS | oui | — | oui | unique | **REUSE** |
| Suggestions | `api.searchSuggestions` | `GET /api/search/suggestions` | idem | oui | liens | oui | — | **REUSE** |
| Command Center ⌘K | `platform-command/*` | `searchElfis` | Engine V1 | oui | navigate | oui | unique UX globale | **REUSE** (pas de 2e ⌘K) |
| SearchPage `/search` | `pages/SearchPage.tsx` | `searchElfis` | Engine V1 | oui | liens | oui | complète CC | **REUSE** |
| GlobalSearchBar | `components/GlobalSearchBar.tsx` | suggestions | Engine V1 | oui | liens | non (orphelin) | doublon mort | **DEFER** retrait |
| Shared Relations | `api.list/searchSharedRelations` | `/api/shared/relations*` | adapters | oui | — | oui | unique | **REUSE** |
| Relations UI | `PlatformRelationsPage` | shared relations | — | oui | nav | lecture | — | **REUSE** |
| Composer ClientStep | était inline → `CustomerPicker` | dual customers + relations | billing + SharedRelation | oui | oui | **oui** | était ad hoc | **ADAPT** → CustomerPicker |
| Composer ProductsStep | inline filtre local | `listCatalog` | billing catalog | local | oui | partiel | ad hoc | **ADAPT** contrat ProductPicker (F1.2 branchement) |
| SalesDocLinesEditor | `<select>` | catalogue | billing | non | oui | partiel | autre UX | **DEFER** unifier |
| Devis client datalist | match nom | customers overview | fragile | faible | oui | non | vs SharedRelation | **DEFER** |
| Documents billing | `billingOverview` | `/billing/sales-overview` | SalesDoc[] | q | — | liste | pas de picker | **ADAPT** → DocumentPicker |
| Vault documents | `listDocuments` / Engine | `/documents`, search | vault | oui | — | oui | — | **REUSE** via Engine scope |
| LauncherSearch | apps local | — | apps | local | open Pilot | oui (autre intent) | — | **REUSE** (ne pas fusionner) |
| Financial CC | dashboard Compta | financial overview | — | non | — | — | homonyme | **DEFER** hors P1.0 |
| Recents CC | `RecentSearches` | localStorage chrome | UX only | — | — | chrome | — | **REUSE** chrome ; **OFF** métier pickers |
| Favoris / top produits | tabs Composer | — | **aucune** | — | — | non | inventé | **OFF** (empty honnête) |
| InventoryPilot | — | — | absente | — | — | contrat | — | **DEFER** F1.2 (`InventoryPilotSource`) |
| useDebouncedSearch partagé | — | — | — | — | — | manquant | — | **ADAPT** → `useSmartSearch` |

## Types indexés Engine V1 (réels)

`vault_document`, `document_*`, `accounting_*`, `customer`, `supplier`, `sales_*` …

**Absents de l’index** comme type dédié : factures/devis/avoirs billing (`SalesDocument`) → DocumentPicker utilise `billingOverview`, pas un fake index.

## Raccourcis

| Raccourci | Owner | P1.0 |
|-----------|-------|------|
| Cmd/Ctrl+K | Command Center | **Conservé** — Smart Search n’enregistre pas de concurrent |
| ↑↓ Enter Escape Tab | combobox pickers / SmartSearch | **Implémenté** localement |

## Permissions / tenant

- Engine : `organization_id` + feature `SEARCH_GLOBAL` + subscription
- Shared Relations : org + permissions lecture documents/factures (mapping temporaire)
- Billing : org via auth header

## Emplacement nouveau code

`frontend/src/platform-search/` — couche UX uniquement.
