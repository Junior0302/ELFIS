# SalesPilot Workspace & Dashboard V1 (S1.2)

**Status:** Live dashboard (server-aggregated KPIs)  
**Non-goals:** Kanban, AI, frontend KPI math, S1.3

## Audit — reuse

| Source | Reuse |
|--------|-------|
| Command Center / Launch Dashboard | Pattern `Service.build()` + single GET |
| Work Queue page | DS `PageHeader` / `Section` / `EmptyState` states |
| Sales CRM S1.1 | Models, soft_alive, `sales.read`, ensure_default_pipeline |
| Design System 1.0 | MetricCard, QuickActionCard, Grid, Container, Badge, Button |

## API

`GET /api/sales/dashboard` → `SalesDashboardService.build`

Returns: `summary`, `pipeline`, `activities`, `tasks`, `recent_opportunities`, `quick_actions`, `generated_at`

## Frontend

`SalesDashboardPage` — one request via `api.getSalesDashboard`. Loading / error / empty states. Desktop 2 columns, mobile stack.
