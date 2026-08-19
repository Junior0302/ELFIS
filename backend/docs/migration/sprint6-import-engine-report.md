# Sprint 6 — Import Engine V1 — Rapport de certification

## Verdict

**SPRINT 6 CERTIFIED**

## Objectif

Transformer les documents `ready_for_import` (Validation & Mapping Center) en données métier ComptaPilot de façon transactionnelle, idempotente, traçable et rejouable.

## Architecture

```
ready_for_import
  → import_pending → importing
  → import_completed | import_failed
  → rollback_completed | import_cancelled
```

Module `backend/app/import_engine/` :

| Fichier | Rôle |
|---------|------|
| `pipeline.py` | Pipeline 14 étapes, commit unique |
| `mapping.py` | Mapping Engine schémas Sprint 4 → Invoice/Contact/Bank |
| `transaction.py` | Enveloppe transactionnelle |
| `rollback.py` | RollbackService (SQL / métier / manuel / auto) |
| `idempotency.py` | ImportFingerprint SHA-256 |
| `validators.py` | Gate Validation & Mapping obligatoire |
| `audit.py` / `events.py` | Traçabilité |
| `api/routes.py` | `/api/import` |

## Pipeline

1. Validation finale (session `ready_for_import`)  
2. Permissions IAM (`import.run`)  
3. Idempotence fingerprint  
4–10. Création/liaison entités + écritures (JSON sur Invoice) + vérifications + commit atomique  
11–14. Audit, events, notification via event bus, statut `import_completed`

## Mapping métier

| Schéma | Objet |
|--------|--------|
| `invoice.v1` | Invoice |
| `quote.v1` | Invoice (`document_type=quote`) |
| `credit_note.v1` | Invoice (`document_type=credit_note`) |
| `receipt.v1` | Invoice (`document_type=receipt`) |
| `bank_statement.v1` | BankAccount + BankTransaction (+ Invoice) |
| `contract.v1` | Invoice (`document_type=contract`) |

Contacts : décisions Sprint 5 uniquement (`use_existing` → lier, `create_later` → créer). Jamais de création automatique hors résolution humaine.

## API

- `POST /api/import/documents/{id}/import`
- `GET /api/import/ready`
- `GET /api/import/imports`
- `GET /api/import/imports/{id}`
- `GET /api/import/imports/{id}/report`
- `POST /api/import/imports/{id}/retry`
- `POST /api/import/imports/{id}/rollback`

## Permissions

`import.read` · `import.run` · `import.rollback` · `import.report`

## Events

`import.started.v1` · `import.mapping.completed.v1` · `import.transaction.started.v1` · `import.transaction.committed.v1` · `import.completed.v1` · `import.failed.v1` · `rollback.started.v1` · `rollback.completed.v1`

## PostgreSQL

Migration additive : `sql/elfis_import_engine_sprint6_postgres.sql`  
Certification : `docs/migration/sprint6-postgres-certification.json` → `"certified": true`

## Frontend

- `MigrationImportPanel` (étape wizard 7 — Migration)
- Documents prêts, résumé, objets créés/liés, progression, rapport, historique
- **Aucun bouton de suppression**

## Preuves

| Contrôle | Résultat |
|----------|----------|
| Tests backend Sprint 6 | 6 PASS |
| Régression Sprint 5 | 6 PASS |
| Tests frontend importApi | 4 PASS |
| Frontend build | OK |
| Routes API | 395 |
| PG cert | certified: true |
| Import partiel | Impossible (commit unique + rollback) |
| Idempotence | Fingerprint actif unique |
| Contournement Validation | Interdit (`ImportValidationError`) |

## Livrables

- Module + SQL + IAM + events + lifecycle
- Panel FE + wizard step 7
- Matrice : `sprint6-requirements-test-matrix.md`
- Preuve PG : `sprint6-postgres-certification.json`
