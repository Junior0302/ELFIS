# 15 — Présentation des graphiques (S1.2.5.1)

## Source

`overview.charts` via `financialApi` :

- `revenue_vs_expenses` → barres groupées  
- `treasury` → ligne + fill  
- `ca_evolution` → ligne + fill  
- `expense_breakdown` — non requis en première rangée Analyser

## Module

`frontend/src/comptapilot/financial-command-center/fccCharts.tsx`

Patterns SVG alignés sur `FinancialDashboardPage.tsx` (axes période, tooltips `<title>`, fill area) **sans** modifier la logique métier `/finance`.

## Règles

| Cas | Comportement |
|---|---|
| 0 point | Widget `empty` |
| 1 point | Message « Historique insuffisant pour afficher une évolution. » — **pas** de fausse courbe |
| ≥ 2 points | SVG + légende (barres) + résumé a11y `visually-hidden` |
| Loading / error | États Widget Framework |

## Hauteur

Corps `WidgetChartBody` : min 210px / max 280px.

## Accessibilité

- `role="img"` + `aria-label`  
- Résumé textuel masqué  
- Tooltips natifs SVG sur points/barres  
