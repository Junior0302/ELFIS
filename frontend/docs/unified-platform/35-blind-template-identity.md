# 35 — Blind template identity

## Principe Design System

ELFIS = **un** Design System. Home / Compta / Sales = **variations de contenu** du même template (`ElfisPageFrame` + `ElfisDashboardTemplate` + primitives).

## Test d’acceptation (blind)

Retirer titres / logos / accents Pilot (vert, bleu, navy métier) :

| Critère | Attendu |
|---------|---------|
| Classes layout parents | `data-elfis-page-frame="v1"` + `data-elfis-dashboard="v1"` + `data-blind-template="v1"` |
| Slots | header → (strip?) → metrics → primary → secondary → actions → (recent-activity?) |
| Variables frame | `--up-page-max-width`, `--up-page-pad-inline`, `--up-dashboard-gap` identiques |
| Wrapper classNames métier | **Absents** : `elfis-home`, `fcc`, `sales-dashboard`, `up-*-unified` (sanitized) |
| Card chrome | `.up-metric-card` / `.up-chart-card` / `.up-surface-card` — mêmes border / radius / shadow |
| Sidebar | navy unique — pas de surface Pilot |

Si un utilisateur peut encore dire « c’est Home / Compta / Sales » sans lire le contenu → **FAIL**.

## Garde-fous code

- `sanitizeDashboardClassName()` retire les classes layout métier du wrapper.
- Contenu peut garder des classes locales **à l’intérieur** des slots (listes, widgets) tant que le chrome est forcé neutre sous `[data-blind-template="v1"]`.

## Tests

`blind-template-identity.test.tsx` — BT01+.
