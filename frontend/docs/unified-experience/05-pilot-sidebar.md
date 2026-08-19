# 05 — PilotSidebar

## Structure commune

- Conteneur `PlatformSidebar` / alias `PilotSidebar`
- Nav métier via `ProductSidebar` + adapters (`ComptaProductNav`, `SalesProductNav`, `HomePlatformSidebar`)
- Largeurs : `--product-sidebar-expanded-width` 240 / `--product-sidebar-collapsed-width` 56
- Collapse sync grille : `ps-shell--sidebar-collapsed` + `useProductSidebarCollapsed`

## Vague 1

| Pilot | Collapse |
|-------|----------|
| Compta | Oui (UI.P1) |
| Sales | **Ajouté** (mêmes dims) |
| Home | Non (rail plateforme fixe) |

Accent sidebar = tokens `--pilot-*` / classes `ps-shell--compta|sales|home` — pas de largeur custom.
