# 28 — Router modal robuste (F1.3.1.3)

## Pattern

Nested route sous Documents + state machine :

| URL | Stage |
|-----|-------|
| `/facturation/documents` | closed (sauf `?create=1` → type_selection) |
| `/facturation/documents?create=1` | type_selection |
| `/facturation/documents/new?type=` | composer |
| `/facturation/documents/new` (sans type) | type_selection **dans** le root (pas Navigate bounce) |
| `/facturation/nouveau?type=` | redirect → `documents/new` |

## Règles

- URL **ne ferme jamais** le modal immédiatement (`closeOnRouteChange: false`).
- Back navigateur depuis `/new` → fermer machine → Documents.
- **Supprimé** : redirect auto si draft vide / pas client / pas lignes / type juste choisi / Composer vide / autosave pas démarré.
- Composer vide = **valide**.
- Type persisté dans `selectedType` (machine) + query `type`.
