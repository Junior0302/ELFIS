# 03 — Live totals

## Source de vérité

Helpers workflow déjà utilisés par le Composer :

- `draftAmountHt` / `draftAmountTva` / `draftAmountTtc`
- Remises lignes via `discountPercent` → `draftDiscountTotal`
- Échéance : `dueDays` + date calendaire locale (`formatDueDateLabel`)

## UX

Composant `LiveTotals` :

- Recalcul immédiat à chaque patch draft
- `aria-live="polite"` + flash discret sur changement TTC
- `prefers-reduced-motion` désactive l’animation

Aucun nouveau calcul métier côté API.
