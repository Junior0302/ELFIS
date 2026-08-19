# Contrôle d'accès documentaire

## Séparation des plans

| Plan | Rôle |
|------|------|
| Permission plateforme IAM | Ops / admin (`storage.*`, `documents.*` catalogue) |
| Rôle organisation | Accès métier ComptaPilot (`documents.read/write/create/...`) |
| Propriété | `owner_user_id` informatif — pas seul critère d'accès |

## Règles

- `organization_id` = contexte auth serveur (membership) — spoof client refusé
- Document autre org → **404** (pas 403 révélateur)
- Lien métier : uniquement sur document de l'org courante
- Quarantine : téléchargement refusé sauf `storage.quarantine.read|manage`
- Soft-deleted / purged : listes masquées, download refusé
- Versions historiques : `documents.versions.read` + `documents.download`
- Legal hold : lecture / manage séparés ; ne donne pas d’accès contenu hors tenant
- Platform admin sans org active / permission explicite ≠ accès contenu

Implémentation : `DocumentAccessPolicy` (`app/storage/document_access_policy.py`).
