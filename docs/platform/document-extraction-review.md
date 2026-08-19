# Revue humaine — Extraction (RC2.5.4)

## Endpoints

- `POST .../extractions/{id}/confirm`
- `POST .../extractions/{id}/reject`
- `POST .../extractions/{id}/correct` — patch champs autorisés
- `POST .../extractions/{id}/reextract` — force + supersede après succès

## Correction

Conserve `provider_value` / `corrected_value` / acteur / date dans l'artefact.  
Journal `elfis_document_extraction_reviews`. Ne pas écraser silencieusement.

## EffectiveExtraction

Ordre : confirmed → completed → partial/invalid → aucun.  
Représentation ELFIS générique — **pas** de sync ComptaPilot.

## Auto-confirm

`DOCUMENT_EXTRACTION_AUTO_CONFIRM=false` par défaut.  
Seuil revue : `DOCUMENT_EXTRACTION_REVIEW_THRESHOLD=0.80`.
