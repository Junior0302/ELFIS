# Sales Collaboration V1 (S1.9)

## Objectif

Collaboration commerciale métier : équipes, ownership, assignations, commentaires, mentions, followers, revues, transferts. **Pas** de chat, messagerie, visioconférence ni sync Slack/Teams.

## Audit (synthèse)

| Fonction | État avant | Limite | Solution |
|----------|------------|--------|----------|
| RBAC | Org-wide sales.* | Pas d’équipe | SalesTeam + permissions collab |
| Ownership | Informel / incomplet | Pas de transfer unifié | Moteur assign + transfer |
| Task owner | `assignee_user_id` | Champ différent | Engine mappe assignee = owner tâche |
| Notes | SalesNote | Pas de mentions | SalesComment + `@[id:Label]` |
| Notifications | Insights + bulk assign | Pas mention/revue | Notifs dédupliquées collab |
| Decision/WQ | Insights only | Hors scope S1.9 | Inchangé |

## Modèles

- `SalesTeam` / `SalesTeamMember` (role lead|manager|member|viewer)
- `SalesComment` (mentions JSON, vault_document_ids, soft delete)
- `SalesFollower`
- `SalesReviewRequest` (pending → approved|changes_requested|rejected)
- `SalesOwnershipTransfer` (audit trail)

SQL : `backend/sql/elfis_sales_collaboration_s19_postgres.sql`

## API `/api/sales/collab/*`

Teams, team-dashboard, assign, transfer, comments, mentions/candidates, followers, reviews, views (`mine|team|assigned|following|to_review`).

## Permissions (ajoutées, S1.x intactes)

`sales.team.read`, `sales.team.manage`, `sales.assign`, `sales.review`, `sales.comment`, `sales.mention`, `sales.transfer`

## Events

`sales.team.*`, `sales.comment.*`, `sales.assignment.*`, `sales.mention.*`, `sales.review.*`, `sales.transfer.*`

## Notifications

Assignation, mention, review, transfer — in-app, dédupliquées. Followers notifiés uniquement sur événements importants.

## Hors scope

Chat, emails auto, Sales AI V2, S2.x, Google/Microsoft collab.
