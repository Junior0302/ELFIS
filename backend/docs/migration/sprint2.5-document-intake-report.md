# Document Intake Engine — Sprint 2.5 Certification Report

**Date:** 2026-07-23  
**Verdict:** **SPRINT 2.5 CERTIFIED**

## 1. Fichiers créés

| Fichier | Rôle |
|---------|------|
| `backend/app/document_intake/doc_id.py` | Universal Document ID |
| `backend/app/document_intake/fingerprint.py` | Fingerprint V2 streaming |
| `backend/app/document_intake/lifecycle_service.py` | Machine à états |
| `backend/app/document_intake/upload_session_service.py` | Upload Sessions |
| `backend/app/document_intake/analytics_service.py` | Analytics backend-only |
| `backend/sql/elfis_document_intake_stage2_5_postgres.sql` | Migration PG additive |
| `backend/tests/document_intake/test_sprint25.py` | Tests Sprint 2.5 |
| `backend/scripts/migration/certify_document_intake_stage2_5_postgres.py` | Certif PG staging |
| `backend/docs/migration/sprint2.5-document-intake-report.md` | Ce rapport |

## 2. Fichiers modifiés

- `backend/app/document_intake/enums.py`, `models.py`, `repository.py`, `service.py`, `schemas.py`, `events.py`, `storage.py`, `api/routes.py`
- `backend/app/events/event_types.py`, `backend/app/config.py`
- `backend/scripts/rc1/migrate_sql.py` (SQL_ORDER + exécution blocs `$$`)
- `backend/tests/document_intake/conftest_helpers.py`
- `frontend/src/services/documentIntakeApi.ts` (+ tests)
- `frontend/src/components/MigrationIntakePanel.tsx`
- `frontend/src/index.css`

## 3. Architecture Storage Provider

- Contrat `StorageProvider` + `LocalStorageProvider`
- Factory `get_storage_provider()` via `DOCUMENT_INTAKE_STORAGE_PROVIDER` / `settings.document_intake_storage_provider`
- Providers futurs déclarés (`s3`, `azure_blob`, `gcs`, `minio`) — non implémentés
- Le service métier n’appelle plus le FS directement

## 4. Universal Document ID

- Format `DOC-YYYY-XXXXXXXX`
- Compteur annuel `elfis_document_doc_id_counters` + `SELECT FOR UPDATE` + verrou process-local
- UNIQUE, immuable, backend-only
- `get_by_universal_document_id(organization_id, …)` avec isolation org

## 5. Machine à états

- Enum complet (contrat futur) + transitions actives Sprint 2.5
- `DocumentLifecycleService` : transition, can_transition, mark_*, cancel
- Idempotence, version optimiste, activités + events + audit sensible

## 6. Tables ajoutées

- `elfis_document_doc_id_counters`
- `elfis_document_upload_sessions`
- `elfis_document_lifecycle_entries`

## 7. Colonnes ajoutées (items)

`universal_document_id`, `upload_session_id`, `lifecycle_status`, storage_*, `fingerprint`, `fingerprint_version`, `duplicate_type`, `duplicate_of_item_id`, `duplicate_confidence`, `duplicate_reason`, `client_upload_id`, `idempotency_key`, chunk fields futurs, `last_activity_at`, `version`

## 8. Backfill

Idempotent dans SQL Stage 2.5 : lifecycle ← status, storage local, fingerprint V2, DOC IDs via compteur, duplicate_type exact.

## 9. Upload Sessions

Token `upl_…`, pause/resume/cancel/expire, compteurs, rattachement migration + org + user.

## 10. Analytics

`UploadAnalyticsService` — JSON sur session, endpoint GET analytics, vitesse `null` si non calculable.

## 11. Fingerprint V2

sha256, size, mime, extension, first/last block hash (64 KiB), ZIP entry count borné.

## 12. Endpoints

Conservés Sprint 2 + :

- `GET /items/{id}/lifecycle`
- `POST|GET /upload-sessions`
- `GET /upload-sessions/{id}`
- `POST …/pause|resume|cancel`
- `GET …/analytics`

Upload/batch acceptent `upload_session_id` + `idempotency_key`.

## 13. Permissions

`document_intake.read` / `upload` / `cancel` (inchangées).

## 14. Événements

+ `document.lifecycle.changed.v1`, upload_session.*, `document.upload.analytics.updated.v1`, `document.fingerprint.created.v1`

## 15. Audit / activités

Création/pause/reprise/annulation session ; transitions sensibles ; titres activité migration lisibles.

## 16. Tests backend

- Sprint 2 : OK  
- Sprint 2.5 : **25 passed** (`tests/document_intake/`)

## 17. Tests frontend

- `documentIntakeApi.test.ts` : **8 passed**  
- `npm run build` : OK

## 18. PostgreSQL staging

Script `certify_document_intake_stage2_5_postgres.py` :

- A/B/C/D : **ok**
- `backfill_ok` : **true**
- `certified` : **true**

## 19. Build

Frontend production build réussi.

## 20. Nombre total de routes

**359** (+8 vs Sprint 2 à 351).

## 21. Risques

- Concurrence DOC ID multi-process : dépend de `FOR UPDATE` PG (verrou process-local = filet in-process)
- Potential duplicate non activé (volontaire)
- Analytics vitesse rarement renseignée sans `completed_at`

## 22. Limites

Pas d’OCR, IA, extraction, antivirus réel, cloud storage, multipart chunké, admin DOC search publique.

## 23. Confirmation non-scope

Aucun OCR / classification IA / extraction / import métier / archivage définitif / connecteur cloud réel n’a été commencé.

## 24. Recommandation Sprint 3

Brancher le Document Analysis Pipeline sur `ready_for_analysis` uniquement, consommer `universal_document_id` + fingerprint, jobs OCR via Job Queue existante, sans bypass lifecycle ni StorageProvider.

---

**SPRINT 2.5 CERTIFIED**
