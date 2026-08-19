# Document Registry ELFIS Core (RC2.4 étape 1)

## Rôle

Registre logique des documents plateforme, distinct de :

- Factures ComptaPilot (`Invoice` + `/api/documents`)
- Vault (`VaultDocument`)
- Document Intelligence (extractions)

## API minimale

Préfixe : **`/api/document-registry`** (évite la collision ComptaPilot).

| Méthode | Chemin | Permission org |
|---------|--------|----------------|
| POST | `/upload` | `documents.create` / `documents.write` |
| POST | `/` | idem (alias streaming) |
| GET | `/` | `documents.read` |
| GET | `/{id}` | `documents.read` |
| GET | `/{id}/download` | `documents.download` / `documents.read` |
| GET | `/{id}/content` | preview inline (PDF/images) |
| POST | `/{id}/links` | `documents.write` / `documents.create` |
| POST | `/{id}/archive` | `documents.archive` / `documents.write` / `documents.manage` |
| POST | `/{id}/unarchive` | `documents.archive` |
| POST | `/{id}/delete` | `documents.delete` |
| POST | `/{id}/restore` | `documents.restore` |
| GET/POST | `/{id}/versions` | `documents.versions.read` / `create` |
| GET | `/{id}/versions/{vid}` | `documents.versions.read` |
| GET | `/{id}/versions/{vid}/download` | download + versions.read |
| POST | `/{id}/versions/{vid}/restore` | stratégie B (nouvelle version) |
| GET/POST | `/{id}/legal-holds` | legal_hold.read / manage |
| POST | `/{id}/legal-holds/{hid}/release` | legal_hold.manage |

Pas d’API de purge physique (CLI uniquement).

Contraintes :

- Auth + organisation obligatoire
- Isolation cross-tenant (404 masqué)
- Streaming + `Content-Disposition` sécurisé
- Aucun chemin physique / URL permanente non protégée

## Permissions IAM plateforme

Catalogue :

- `storage.objects.read|create|delete|purge`
- `documents.read|create|archive|download|manage`
- `documents.versions.read|create`
- `documents.delete|restore`
- `documents.legal_hold.read|manage`
- `documents.retention.read|manage`

`storage.objects.purge` / `documents.retention.manage` : **super_admin** uniquement (pas platform_admin).

## Audit

Événements étape 1–2 + étape 3 : `DOCUMENT_VERSION_*`, `DOCUMENT_UNARCHIVED`, `DOCUMENT_SOFT_DELETED`, `DOCUMENT_RESTORED`, `DOCUMENT_LEGAL_HOLD_*`, `DOCUMENT_PURGE_*`, `DOCUMENT_RETENTION_EVALUATED`.

Métadonnées autorisées : ids, taille, MIME, source, statut, version_number, retention_rule, blocked_reason — **jamais** le contenu fichier ni le chemin complet.

## Tables

- `elfis_storage_objects`
- `elfis_document_records`
- `elfis_document_links`
- `elfis_document_versions`
- `elfis_document_legal_holds`
- `elfis_document_tombstones`

SQL : `backend/sql/elfis_storage_documents_postgres.sql` (+ stage2 / stage3)
