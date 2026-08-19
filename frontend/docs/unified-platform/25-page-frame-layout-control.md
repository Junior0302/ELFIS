# 25 — Page frame layout control

## Cause

Les composants partagés (`PlatformPageContainer`, grilles locales) **n’imposaient pas** la largeur finale :

| Écran | Wrapper restrictif | Effet |
|-------|-------------------|--------|
| Home | `max-width: 1480px` + `padding="sm"` + viewport pad dédié | Largeur / densités propres |
| FCC | `PlatformPageContainer` xl (1200) + `.fcc-kpi-grid` 8 cols ad hoc | Full-bleed relatif + grille KPI cassée |
| Sales | `ElfisDashboardTemplate` → `PlatformPageContainer` xl (1200) | « Colonne étroite » vs Home |

Résultat : à viewport identique, proportions divergentes.

## Avant → Après

| | Avant | Après |
|---|--------|--------|
| Source largeur | 3 chemins (1480 / 1200 / 1200) | **Une** : `ElfisPageFrame` (`--up-page-max-width: 100rem` ≈ 1600px) |
| Parent layout | Décoration autour d’anciens containers | `ElfisPageFrame` → `ElfisDashboardTemplate` |
| Composition | Grilles / paddings page-local | header → strip → metrics → main 8/4 → actions → footer |
| Home / FCC / Sales | Wrappers distincts | Même frame + mêmes classes padding / grid |

## Règle GO

1. Aucune de ces 3 pages n’ajoute un `max-width` &lt; frame (960 / 1100 / 1200 / 1480).
2. `data-elfis-page-frame="v1"` est l’ancêtre layout réel.
3. `data-elfis-dashboard="v1"` + `.up-dashboard__grid.up-grid--cols-12` présents.
4. Tests : `page-frame-layout.test.tsx` + UXU08b / UXU22 / UXU61.

## Fichiers

- `primitives/ElfisPageFrame.tsx` (nouveau)
- `primitives/ElfisDashboardTemplate.tsx` (frame + slots strip/actions)
- `ElfisHomePage.tsx`, `FinancialCommandCenter.tsx`, `SalesDashboardPage.tsx`
- `unified-platform.css`, `platformTokens.ts`, `home.css`

## STOP

Layout GO pour revue. Pas de migration pages secondaires. Pas de commit.
