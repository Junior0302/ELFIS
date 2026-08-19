# Providers OCR (RC2.5.3)

## Contrat `OCRProvider`

Propriétés : `provider_key`, `provider_version`, `capabilities`, MIME, langues, limites, flags natif/image/PDF/confiance/bbox.

Méthode : `async recognize(OCRRequest) -> OCRProviderResult`

Le provider **ne persiste jamais** en base.

## Capabilities

`OCRProviderCapabilities` : pdf, images, multipage, native_text, confidence, bounding_boxes, tables, handwriting, language_detection, orientation_detection.

L’orchestrateur vérifie les capacités avant exécution. Ne pas supposer confiance / bbox / langue / tables.

## Registre

`DOCUMENT_OCR_PROVIDER=noop|native_pdf|tesseract|external`

- Inconnu → refus au démarrage / health
- Injectable en tests
- Aucun secret exposé

## Providers livrés

| Key | Rôle |
|-----|------|
| `noop` | Tests / orchestration — **ne lit pas le fichier** |
| `native_pdf` | Extraction texte PDF via **pypdf** (lecture seule) — `extraction_method=native_pdf_text` |

### noop

Modes : `ok`, `retryable`, `permanent`, `timeout`, `low_confidence` (+ pages simulées).

### native_pdf_text

- Limite pages / caractères / timeout
- PDF chiffré / corrompu → erreur sanitisée
- Pas de JS, pas de liens externes, pas d’écriture

### Tesseract / cloud

Non activés par défaut. Configuration explicite requise ; binaire non assumé ; jamais `shell=True`.

## Sélection (`OCRProviderSelectionService`)

1. PDF texte natif suffisant → `native_pdf` (si enabled)
2. PDF scanné → provider OCR configuré
3. Image → provider image
4. MIME non supporté → échec non retryable / skipped

Résultat explicable : `selected_provider`, `reason_code`, `fallback_chain`, `capabilities_checked` — **sans filename**.

## API publique providers

`GET /api/document-processing/ocr/providers` — key, disponibilité, capacités, langues, limites non sensibles. Jamais clé API / chemin binaire / config secrète.
