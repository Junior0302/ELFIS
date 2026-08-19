# RC2.5.2 — Validation Document Classification

```bash
cd backend
export ELFIS_ENVIRONMENT=test
python scripts/rc2/validate_document_classification_stage2_staging.py
```

Couverture : PDF facture/devis/ambigu, jobs, scores, revue, reject, reclassify, tenant, cleanup.
Hors scope : OCR, IA, lecture texte PDF.
