# RC2.5.1 — Validation Document Processing Stage 1

## Prérequis

- Backend avec SQL `elfis_document_processing_stage1_postgres.sql` appliqué (ou `create_all` tests)
- `ELFIS_ENVIRONMENT` défini
- Document probe registre (pas de document réel client)

## Script

```bash
cd backend
python scripts/rc2/validate_document_processing_stage1_staging.py
```

## Couverture attendue

- Création job + étapes
- Idempotence
- Worker `--once` / noop pipeline
- Progression → completed
- Retry volontaire
- Annulation
- Lease expirée + récupération
- Isolation tenant
- Audit + System Health
- Nettoyage

## Hors scope

Aucun OCR, IA, extraction comptable, upload ComptaPilot.
