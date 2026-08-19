# RC2.4 étape 2 — Secure Upload & Tenant-Safe Download

## Audit initial (résumé)

- Upload étape 1 : `await file.read()` en mémoire complète
- Org résolue via `AuthContext` / `X-Organization-Id` (membership)
- Cross-tenant → **404** masqué
- Compensation basique déjà présente ; pas de streaming ni quarantaine opérationnelle
- Content-Disposition partiellement sécurisé ; nosniff présent

## Architecture retenue

1. Validation nom/params  
2. Écriture streaming vers `_temp` (chunks + SHA-256 + compteur)  
3. Validation MIME/magic finale  
4. Promotion atomique → `default` ou `quarantine`  
5. Persist `ElfisStorageObject` + `ElfisDocumentRecord` (+ liens)  
6. Commit DB  
7. Audit non bloquant  

Échec DB après stockage → compensation (`delete` nouvel objet) + audit `STORAGE_OBJECT_COMPENSATED` / orphelin.

## Endpoints

| Méthode | Chemin |
|---------|--------|
| POST | `/api/document-registry/upload` |
| POST | `/api/document-registry` (alias streaming) |
| GET | `/api/document-registry` (filtres + total isolé) |
| GET | `/api/document-registry/{id}` |
| GET | `/api/document-registry/{id}/download` |
| GET | `/api/document-registry/{id}/content` (inline PDF/images) |
| POST | `/api/document-registry/{id}/links` |
| POST | `/api/document-registry/{id}/archive` |

## Permissions

- Org : `documents.create|write|read|download|archive`
- IAM : `storage.quarantine.read|manage` (inspection quarantaine)
- Platform roles ≠ accès contenu client sans org + permission

## CLI

```bash
python -m scripts.storage.cleanup_temp --preview
python -m scripts.storage.cleanup_temp --execute --older-than-hours 24 --confirm
python -m scripts.storage.find_orphans --preview
```

## Validation

```bash
python -m pytest tests/storage -q --tb=line
python scripts/rc2/validate_storage_stage2_staging.py
# staging PG : --apply-sql / --db-only si pas de disque persistant
```

## Limites

- Pas d’antivirus, OCR, IA, S3, Supabase Storage
- Pas de migration ComptaPilot `/api/documents`
- Frontend : permissions membership org (IAM plateforme complète pas toujours chargée)
