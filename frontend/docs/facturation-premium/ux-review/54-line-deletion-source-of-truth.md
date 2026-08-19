# 54 — Line deletion source of truth

## Source unique

`draft.products` (avec `lineKey` stable) — unique collection pour éditeur, preview, totaux, validations, insights, autosave.

## API parent

| Helper | Rôle |
|--------|------|
| `replaceProducts` | Remplace la liste (éditeur / remove) via `setDraft` fonctionnel |
| `appendProduct` | Append `d => [...d.products, next]` — pas de closure stale |
| `draftRef` + `draftEpochRef` | Snapshot / last-write-wins autosave |

## Interdit

- `lastPicked` / `selected={…}` ProductPicker comme copie visuelle de ligne  
- `[...draft.products, x]` pour les ajouts  
- Keys React = index seul
