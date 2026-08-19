# 04 — Composants

Tous dans `frontend/src/insight-framework/` — utiles seulement, pas de surarchitecture.

| Composant | Usage |
|-----------|--------|
| **InsightCard** | Carte complète (header, summary, Pourquoi ?, actions, footer) |
| **InsightInline** | Ligne compacte (validation Composer, listes denses) |
| **InsightBanner** | Bandeau horizontal (setup / annonces) |
| **InsightToast** | Notification courte `role="status"` |
| **InsightList** | Liste triable / empty state |
| **InsightStack** | Pile limitée (max N) |
| **InsightBadge** | Pastille type (+ option severity) |
| **InsightIcon** | Icône SVG sémantique |
| **InsightActions** | Groupe CTA |
| **InsightHeader** | Badge + titre |
| **InsightFooter** | Source / confiance / timestamp (si fournis) |

## Zone « Pourquoi ? »

Si `details` présent et `expandable !== false` → bouton **Pourquoi ?** (`aria-expanded` / `aria-controls`).

## Props communes

`insight`, `className`, `onDismiss`, `renderAction` (ex. `Link` React Router côté FCC).
