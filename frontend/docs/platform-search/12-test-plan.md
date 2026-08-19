# 12 — Plan de tests PSS01–PSS40

## Automatisés (vitest)

| ID | Cas | Couverture |
|----|-----|------------|
| PSS01 | Adapter Engine → SearchResult | unit |
| PSS02 | Adapter SharedRelation / customer | unit |
| PSS03 | Adapter SalesDoc / catalog | unit |
| PSS04 | mapEngineResourceType | unit |
| PSS05 | groupResultsByType | unit |
| PSS06 | handleListKeyboard ↑↓ Enter Escape | unit |
| PSS07 | GLOBAL_SHORTCUT_OWNER = Command Center | unit |
| PSS08 | ProductSource local available | unit |
| PSS09 | InventoryPilotSource unavailable | unit |
| PSS10 | searchResultToCustomerSelection opaque id | unit |
| PSS11 | catalogResultToLineFields | unit |
| PSS12 | DISABLED_RECENTS / FAVORITES | unit |
| PSS13 | CustomerPicker rend combobox | rtl |
| PSS14 | CustomerPicker sélection SharedRelation | rtl |
| PSS15 | CustomerPicker fallback billing | rtl |
| PSS16 | ProductPicker empty honnête | rtl |
| PSS17 | DocumentPicker utilise billing (mock) | rtl |
| PSS18 | SupplierPicker scope suppliers | rtl |
| PSS19 | Pas d’appel fuzzy FE (adapters purs) | unit |
| PSS20 | Command Center toujours owner ⌘K (const) | unit |

## Manuels

| ID | Cas |
|----|-----|
| PSS21 | Debounce 2+ chars scope global |
| PSS22 | Abort / frappe rapide |
| PSS23 | Composer `/facturation/nouveau` sélection client SharedRelation |
| PSS24 | Composer sélection client billing |
| PSS25 | Composer création client |
| PSS26 | Ouvrir Relations depuis picker |
| PSS27 | Cmd/Ctrl+K ouvre Command Center (pas double palette) |
| PSS28 | Command Center recherche Engine intacte |
| PSS29 | DocumentPicker facture/devis/avoir |
| PSS30 | ProductPicker catalogue local |
| PSS31 | Inventory message honnête si prefer inventory |
| PSS32 | États empty / error / offline |
| PSS33 | A11y : lecteurs d’écran combobox |
| PSS34 | Tenant orgId respecté (changement org) |
| PSS35 | Permissions insuffisantes → error UI |
| PSS36 | Partial results si une source dual échoue |
| PSS37 | Build `npm run build` vert |
| PSS38 | Tests ciblés platform-search verts |
| PSS39 | Pas de régression calculs facturation |
| PSS40 | Docs 01–13 présentes |

## Exécution

```bash
cd frontend
npm test -- src/platform-search
npm run build
```
