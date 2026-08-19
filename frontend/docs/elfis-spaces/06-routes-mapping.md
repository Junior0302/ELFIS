# 06 — Mapping routes

Routes **existantes** uniquement. Pas de pages inventées.

| Espace | Entrée | Raccourcis |
|--------|--------|------------|
| Finance | `/dashboard` | `/facturation`, `/tva`, `/banque` |
| Commercial | `/sales` | `/sales/pipeline`, `/sales/leads`, `/sales/proposals` |
| Documents | `/platform/documents` | coffre `/platform/documents` |
| RH | — | — (Bientôt) |
| Analyse | — | — (Bientôt) |
| Support | — | — (Bientôt) |

> Note : l’API Sales `GET /api/sales/dashboard` n’est pas une route SPA.
> L’entrée commerciale reste `/sales` (dashboard SalesPilot).

## Footer

| Label | Route |
|-------|-------|
| Accueil ELFIS | `/home` |
| Organisation | `/platform/organization` |
| Documents | `/platform/documents` |
| Relations | `/platform/relations` |
| Communications | `/platform/communications` |
| Paramètres | `/platform/settings` |

## Produits

`PRODUCT_ENTRY_ROUTES` inchangé pour moteurs (`comptapilot` → `/dashboard`, `salespilot` → `/sales`).
`getKnownSpaRoutes()` ajoute `/platform/documents` pour l’espace Documents.
