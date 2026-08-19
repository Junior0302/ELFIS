# Validation staging — Document Extraction RC2.5.4

```bash
cd backend
set ELFIS_ENVIRONMENT=staging
python -m scripts.rc2.validate_document_extraction_stage4_staging --provider noop
# --provider rules
```

Probes uniquement (PDF/OCR générés) — aucun document utilisateur, aucune IA, aucune publication ComptaPilot.

Non-régression :

```bash
python -m pytest tests/document_extraction tests/document_ocr tests/document_classification tests/document_processing -q --tb=line
python -m pytest tests/storage tests/audit tests/iam tests/system_health tests/platform_admin -q --tb=line
```
