# 03 — Widgets

Réutilise **ELFIS Widget Framework** (`frontend/src/widget-framework/`) — pas de second framework.

| Widget | Variant | Source données |
|---|---|---|
| Charts Analyser | `chart` | `overview.charts.*` |
| KPI Essentiel | `compact` | `overview.kpis` + docs (+ banques si sync signal) |
| Priorités / Alertes | `list` | `buildDayPriorities` / `overview.alerts` |
| Health | `score` | `overview.health` + `recommendations` |
| Prévisions | `standard` (empty premium custom) | aucun champ forecast API → empty |
| Activité | `list` + timeline CSS | `overview.recent_activity` |
| Assistant | `hero` | lien `/copilote` + 1er recommendation |

## Refresh

- Global : bouton **Actualiser** → `financialApi.overview(..., true)`
- Par widget : toolbar Actualiser (aria-label)
- Intervalle 60s inchangé
