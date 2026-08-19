# SalesPilot Pipeline Engine V1 (S1.3)

**Status:** Commercial pipeline board (not a generic Kanban)  
**Non-goals:** Full opportunity detail page, AI, S1.4

## API

- `GET /api/sales/pipeline` — board (stages → cards → summary)
- `POST /api/sales/pipeline/opportunities/{id}/move` — validated stage change + events + 409 rollback
- `GET /api/sales/pipeline/opportunities/{id}/drawer` — quick detail

## Backend rules

- Health score 0–100 (deterministic)
- Aging labels
- Risk low/medium/high/critical
- `stage_entered_at` for time-in-stage

## Frontend

Desktop horizontal board + HTML5 DnD with optimistic UI + rollback.  
Mobile stacked list + stage `<select>`.  
Drawer (Design System) for quick detail.
