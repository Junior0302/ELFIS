# SalesPilot Relationship Workspace V1 (S1.4)

**Status:** écran principal CRM unifié  
**Non-goals:** édition riche, IA, S1.5

## Audit (réemploi)

Lead / Company / Person / Opportunity / Task / Activity / Notes / Attachments (Vault) /
Search / Drawer / Dashboard / Pipeline — une seule architecture workspace, pas de fiches parallèles.

## API

- `GET /api/sales/workspace/{entity}/{id}` — `entity` ∈ lead|company|person|opportunity
- Permission : `sales.read`
- Agrégation : `RelationshipWorkspaceService` (header, summary, contacts, opportunities,
  activities, tasks, notes, attachments, timeline, health, relationship, quick_actions)

## Scores

- **Health** : règles S1.3 (réutilisées)
- **Relationship** : 0–100 déterministe (activités, récence, contacts, complétude, ancienneté)
  — labels Excellent / Bon / Correct / Fragile

## Events

- `sales.workspace.opened.v1`
- `sales.relationship.updated.v1`
- `sales.timeline.updated.v1`

## Frontend

- Route : `/sales/workspace/:entity/:id`
- Page : `RelationshipWorkspacePage` (Design System only)
- Search `action_url` → workspace
- Cartes pipeline → workspace (aperçu drawer conservé)

## Documents

Référence Vault uniquement (`vault_document_id`) — aucun stockage parallèle.
