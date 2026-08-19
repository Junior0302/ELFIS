# 10 — Responsive & accessibilité

## Responsive (S1.2.5.1)

- Desktop : charts 3 cols ; KPI jusqu’à 8 cols ; Comprendre 3 cols ; Bas 30/42/28
- ≤1200px : KPI 4 cols
- ≤960px : Bas empilé
- ≤720px : grilles → 1 col ; **ordre métier** via `order` :
  - Priorités → Alertes → Trésorerie → Impayés → TVA → Actions → autres KPI → Comprendre → Graphiques → Bas
- Boutons d’action en wrap

## Accessibilité

- Titres de section `aria-labelledby`
- Widgets : labels, alertes, status live
- Charts : `role="img"`, tooltips SVG, résumé `visually-hidden`
- Refresh : `aria-label` explicite
- Contraste via tokens navy / surfaces
- `prefers-reduced-motion` sur skeleton framework
- Vert en accent produit uniquement (pas imposé framework)

## Clavier

Liens et boutons natifs ; refresh widget focusable.
