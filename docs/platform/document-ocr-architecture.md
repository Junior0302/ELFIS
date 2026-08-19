# Architecture — Document OCR (RC2.5.3)

## Périmètre

Framework OCR générique + artefacts texte sécurisés.
**Pas** d’extraction comptable, **pas** d’IA générative, **pas** de fusion avec la classification.

## Séparation des responsabilités

| Module | Rôle |
|--------|------|
| `app/storage` | Octets documentaires, versions, rétention |
| `app/document_processing` | Jobs / steps / worker |
| `app/document_processing/ocr` | Contrat provider, sélection, résultats, artefacts |

Storage fournit les octets. OCR produit texte + métadonnées. L’extraction métier viendra plus tard.

## Vocabulaire

| Terme | Sens |
|-------|------|
| **OCRJob** | `ProcessingJob` avec pipeline `document_ocr_v1` |
| **OCRResult** | Résultat global lié à une **version** précise |
| **OCRPageResult** | Résultat d’une page |
| **OCRProvider** | Moteur `recognize(request) → result` (n’écrit pas en DB) |
| **NativeTextExtraction** | Texte PDF sélectionnable — **pas** de l’OCR image |
| **OCRArtifact** | Blob UTF-8/JSON privé (`processing-artifacts`) |

## Pipeline `document_ocr_v1`

1. `validate_document_available`
2. `inspect_storage_metadata`
3. `select_ocr_provider`
4. `prepare_ocr_input`
5. `perform_ocr`
6. `persist_ocr_artifact`
7. `finalize_ocr_result`
8. `finalize_processing`

Distinct de `document_basic_v1` et `document_classification_v1`.

## Versioning

Un `OCRResult` appartient à un `document_version_id`.
La version N+1 n’hérite jamais silencieusement du texte de la version N.
Une restauration créant une nouvelle version implique un nouveau job si besoin.

## Idempotence

Clé logique : `(document_version_id, provider_key, provider_version)` + options normalisées.
- Résultat actif complet → réutilisation
- `force=true` → supersède l’ancien (`superseded`) et crée un nouveau résultat

## Classification

RC2.5.2 reste inchangé. Un futur `TextBasedDocumentClassifier` n’est **pas** activé.

## Défauts sûrs

- `DOCUMENT_OCR_ENABLED=false`
- `DOCUMENT_OCR_PROVIDER=noop`
- `DOCUMENT_OCR_AUTO_ENQUEUE=false`
- Aucun worker OCR automatique dans l’API production
