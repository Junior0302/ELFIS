# 21 — Relations API

Base : `/api/shared/relations` (org courante, subscription active)

| Méthode | Route | Description |
|---------|-------|-------------|
| GET | `/` | Liste paginée + filtres q/role/source/status |
| GET | `/search` | Recherche |
| GET | `/duplicates` | Doublons org (auto_merge=false) |
| GET | `/{id}` | Détail + usages + doublons |
| GET | `/{id}/roles` | Rôles |
| GET | `/{id}/duplicates` | Doublons de la fiche |

Permissions (mapping temporaire) : `invoice.read` | `documents.read` | `ai.analysis` | `*`

Isolation : filtre strict `organization_id`.

Audit : `shared_relations.*` via `write_audit`.
