# Validation staging — Document OCR RC2.5.3

## Script

```bash
cd backend
set ELFIS_ENVIRONMENT=staging
python -m scripts.rc2.validate_document_ocr_stage3_staging --provider noop
# options : --provider native_pdf | --apply-sql | --keep-probes
```

## Couverture probes

- PDF texte natif généré (pas de document utilisateur)
- Job `document_ocr_v1`
- Sélection provider
- Résultat + pages + artefact
- Streaming texte (métadonnées audit sans contenu)
- Retry / timeout simulé (noop)
- Isolation tenant
- Health OCR
- Quarantaine → blocked
- Nettoyage

## Non-régression recommandée

```bash
python -m pytest tests/document_ocr tests/document_classification tests/document_processing -q --tb=line
python -m pytest tests/storage tests/audit tests/iam tests/system_health tests/platform_admin -q --tb=line
cd ../frontend && npm run build
```

## Limites connues

- Provider `noop` : healthy en test mais **ne produit pas d’OCR réel**
- Tesseract / cloud : non activés sans config explicite
- Timeout coopératif (asyncio) — pas un kill hard du binaire externe
- Validation PostgreSQL `FOR UPDATE SKIP LOCKED` à confirmer sur l’environnement déployé
