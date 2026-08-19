# Architecture — Document Processing (RC2.5.1)

## Séparation Storage / Processing

| Module | Responsabilité |
|--------|----------------|
| `app/storage` | Fichiers, objets, versions, lifecycle, providers |
| `app/document_processing` | Jobs, étapes, orchestration, worker, retry |

Aucun OCR, IA, extraction comptable ou migration ComptaPilot dans cette étape.

## Vocabulaire

- **ProcessingJob** — traitement global pour un document/version
- **ProcessingStep** — unité de travail ordonnée
- **ProcessingAttempt** — tentative d’exécution d’une étape
- **ProcessingPipeline** — définition code (pas de code arbitraire en base)

Pipeline initial : `document_basic_v1`

1. `validate_document_available`
2. `inspect_storage_metadata`
3. `noop_processing`
4. `finalize_processing`

## Queue

File PostgreSQL persistante (`FOR UPDATE SKIP LOCKED`), fallback SQLite pour tests.
Les jobs survivent au redémarrage API. Pas de BackgroundTasks FastAPI comme seule garantie.
Worker hors processus HTTP : `python -m scripts.processing.worker`

## Leases

Champs `locked_at`, `locked_until`, `locked_by`, `heartbeat_at`.
Un seul worker détient le job ; leases expirées récupérables.

## Auto-enqueue / Outbox

`DOCUMENT_PROCESSING_AUTO_ENQUEUE=false` par défaut.
Aucune outbox plateforme dédiée créée dans RC2.5.1 : le mode manuel suffit.
Si l’auto-enqueue est activé plus tard, un outbox transactionnel ou enqueue post-commit sera requis.

## Classification (RC2.5.2)

Pipeline `document_classification_v1` : validate → inspect → classify → persist → finalize.
Classifiers déterministes (metadata, filename keywords, structure MIME) — **score heuristique**.
Voir `docs/platform/document-classification.md`.

## OCR (RC2.5.3)

Pipeline `document_ocr_v1` : validate → inspect → select → prepare → perform → persist artifact → finalize OCR → finalize.
Providers : `noop` (défaut tests), `native_pdf` (texte PDF, pas OCR image). Artefacts hors colonnes JSON.
Voir `docs/platform/document-ocr-architecture.md`.

## Extraction (RC2.5.4)

Pipeline `document_extraction_v1` : type effectif → schéma → source OCR → load → perform → validate → persist → finalize.
Providers : `noop`, `rules`. Consomme uniquement OCRResult de la même version. Pas d'IA / ComptaPilot.
Voir `docs/platform/document-extraction-architecture.md`.
