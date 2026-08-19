# 09 — Performance

## Chargement

- Un appel principal : `financialApi.overview(token, orgId[, refresh])`
- Pas de waterfall KPI/alerts/charts séparés en V1 (overview les embarque)

## Refresh

| Mode | Comportement |
|---|---|
| Bouton « Actualiser tout » | `overview(..., true)` — état `refreshing` |
| Bouton widget | même reload overview (pas de reload page) |
| Intervalle 60 s | refresh silencieux (`refreshing`, pas flash `loading`) |

## Ce qui n’est pas fait (V1)

- Pas de cache IndexedDB
- Pas de SSR
- Pas de second Financial Engine client
