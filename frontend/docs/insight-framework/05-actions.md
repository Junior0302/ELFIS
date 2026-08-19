# 05 — Actions

## Kinds standard

| Kind | Label FR défaut |
|------|-----------------|
| `view` | Voir |
| `fix` | Corriger |
| `dismiss` | Ignorer |
| `retry` | Réessayer |
| `open` | Ouvrir |
| `understand` | Comprendre |
| `custom` | (label obligatoire) |

Helper : `createInsightAction(kind, overrides)`.

## Comportement

- `href` → lien (`<a>` ou `renderAction` custom)
- `onClick` → bouton
- `dismissible` + `onDismiss` → action **Ignorer** additionnelle
- `primary` → emphase visuelle
- `disabled` / `ariaLabel` supportés

Aucun CTA inventé : le mapper ne crée une action que si la source fournit un label / href réel (ex. `alert.action`, `priority.actionLabel` + `href`).
