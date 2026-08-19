# SalesPilot Deal Workspace V1 (S1.5)

**Status:** cockpit commercial d’une opportunité  
**Non-goals:** IA, signature électronique, Quote Engine complet, S1.6

## Audit (réemploi)

Opportunity, Relationship Workspace (S1.4), Pipeline, Health, Relationship Score, Vault,
Activities, Tasks, Notes, Timeline — pas d’architecture parallèle.

## API

- `GET /api/sales/opportunities/{id}/workspace` — DealWorkspaceService
- `POST/PATCH/DELETE /api/sales/opportunities/{id}/products`
- `POST /api/sales/opportunities/{id}/participants`

## Forecast

`weighted = estimated_amount × probability / 100` (backend only)

## Events

- `sales.deal.opened.v1`
- `sales.forecast.updated.v1`
- `sales.product.added.v1`
- `sales.product.removed.v1`

## Frontend

- Route : `/sales/deals/:id`
- Page : `DealWorkspacePage` (Design System)
- Pipeline / Search → deal workspace
