# Sales Operations V1 (S1.8)

## Objectif

Couche opérationnelle SalesPilot : productivité commerciale sans nouveau moteur IA.

## Endpoints `/api/sales/ops/*`

| Route | Méthode | Rôle |
|-------|---------|------|
| `/saved-views` | GET/POST | Vues enregistrées |
| `/saved-views/{id}` | PATCH/DELETE | Renommer / défaut / soft delete |
| `/calendar` | GET | Événements (activités, tâches, closings, propositions) |
| `/import/preview` | POST | Simulation CSV (leads/companies/people) |
| `/import/commit` | POST | Import réel, skip doublons optionnel |
| `/duplicates/{resource}` | GET | Scan déterministe (email / nom) |
| `/duplicates/resolve` | POST | `ignore` / `link` / `manual_merge_prepare` — **jamais de fusion auto** |
| `/bulk` | POST | Actions groupées (`confirm=true` obligatoire) |
| `/journal` | GET | My Activity (30 jours) |

## Permissions

- Lecture : `sales.read`
- Écriture import / vues : `sales.write`
- Bulk / resolve doublons : `sales.manage`

## Bulk actions supportées

- `soft_delete` (leads, companies, people, opportunities, tasks, activities, notes)
- `mark_done` (tasks)
- `assign` / `change_stage` (opportunities)
- Confirmation obligatoire

## Notifications

In-app uniquement, dédupliquées :

- assignation opportunité (bulk assign)
- insights high/critical (S1.7)

Pas d’e-mail commercial, pas de spam.

## SQL

`backend/sql/elfis_sales_operations_s18_postgres.sql` — table `sales_saved_views`.

## Performance

- Calendar : plage max 92 jours, limits par type
- Import : 500 lignes max
- Journal : 100 items max
- Duplicate scan : 200 enregistrements / resource

## Hors scope S1.8

- Google Calendar / Outlook
- Fusion automatique de doublons
- Sales AI V2 / S1.9
