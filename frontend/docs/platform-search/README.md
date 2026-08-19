# ELFIS Platform Search — Smart Search & Universal Pickers V1

| Champ | Valeur |
|-------|--------|
| **Phase** | P1.0 |
| **Statut** | Livré (couche UX + contrats) |
| **Moteur fuzzy** | Search Engine V1 existant — **non recréé** |
| **Code** | `frontend/src/platform-search/` |

## Objectif

Couche **UX + contrats communs** pour exploiter uniformément Search Engine V1 et les APIs domaine (SharedRelations, catalogue, documents billing), sans second moteur.

## Index docs

| # | Document |
|---|----------|
| 01 | [Runtime audit](./01-runtime-audit.md) |
| 02 | [Contract](./02-contract.md) |
| 03 | [UX Smart Search](./03-ux-smart-search.md) |
| 04 | [Picker framework](./04-picker-framework.md) |
| 05 | [Relation pickers](./05-relation-pickers.md) |
| 06 | [Document picker](./06-document-picker.md) |
| 07 | [Product picker](./07-product-picker.md) |
| 08 | [Keyboard](./08-keyboard.md) |
| 09 | [Security / tenant](./09-security.md) |
| 10 | [Performance](./10-performance.md) |
| 11 | [Integration guide](./11-integration-guide.md) |
| 12 | [Test plan PSS01–PSS40](./12-test-plan.md) |
| 13 | [Implementation report](./13-implementation-report.md) |

## Capacités Core (Blueprint)

- **Smart Search** — normalisation `SearchResult`, scopes, debounce, états, a11y combobox
- **Universal Pickers** — `RelationPicker`, `CustomerPicker`, `SupplierPicker`, `DocumentPicker`, `ProductPicker`

## Non-objectifs P1.0

- Pas F1.2 Smart Library / InventoryPilot
- Pas de 2e raccourci global Cmd/Ctrl+K (Command Center owner)
- Pas de localStorage métier pour favoris/récents
- Pas de nouveaux endpoints pour types absents

## Entrée code

```ts
import {
  SmartSearch,
  CustomerPicker,
  ProductPicker,
  useSmartSearch,
  GLOBAL_SHORTCUT_OWNER,
} from '../platform-search'
```
