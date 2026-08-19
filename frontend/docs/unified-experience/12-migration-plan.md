# 12 — Migration plan

## Flag

`isUnifiedPlatformUiEnabled()` — défaut **true**.  
Opt-out : `VITE_UNIFIED_PLATFORM_UI=false` ou `localStorage elfis.unifiedPlatformUi=0`.

Sous flag off : classes `up-shell--unified` / `up-page--unified` non appliquées ; PlatformShell reste fonctionnel.

## Ordre

1. ~~Vague 1 shell 3 entrées~~ (fait)
2. Vague 2 : header + KPI Home/Compta/Sales dashboards
3. Vague 3 : tables / empty / listes
4. Vague 4 : pages secondaires (après validation visuelle)

## Règles

- Non destructif — adapters métier gardent leurs routes
- Réutiliser UI.P1/P2
- Pas de dual DS
