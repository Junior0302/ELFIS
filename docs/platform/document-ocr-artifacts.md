# Artefacts OCR (RC2.5.3)

## Principe

Le texte OCR **n’est pas** stocké dans les colonnes JSON ordinaires PostgreSQL.
Il vit dans un `StorageObject` privé (namespace `DOCUMENT_OCR_ARTIFACT_NAMESPACE`, défaut `processing-artifacts`).

## Schéma `ocr_text_v1`

```json
{
  "schema_version": "ocr_text_v1",
  "document_version_id": "...",
  "provider": "noop",
  "provider_version": "1.0.0",
  "extraction_method": "noop",
  "pages": [{ "page_number": 1, "text": "...", "confidence": 0.91 }]
}
```

Interdit dans l’artefact : chemin physique, URL signée, token, secret, metadata utilisateur inutile.

## Tables

- `elfis_document_ocr_results` — métadonnées (checksum, longueur, statut, provider…)
- `elfis_document_ocr_pages` — métadonnées page (pas de texte volumineux)

## Accès

`GET /api/document-processing/ocr-results/{id}/text`

- tenant + `document_processing.ocr.text.read`
- document / version valides
- stream artefact
- `X-Content-Type-Options: nosniff`
- `Cache-Control: private, no-store`
- jamais `object_key` en réponse
- audit `DOCUMENT_OCR_TEXT_ACCESSED` (sans contenu)

Les listes API ne contiennent **jamais** le texte OCR.

## Limites

`DOCUMENT_OCR_MAX_*` / `DOCUMENT_OCR_ARTIFACT_MAX_BYTES` — refus avant traitement ou `partially_completed` / `failed` ; jamais d’artefact non borné.

## Temporaires

Stream storage → tempfile sécurisé → provider → `finally` unlink.
Permissions restreintes, nom aléatoire, pas d’extension utilisateur, aucun chemin en audit.

## Rétention / purge

- Lié à la version documentaire
- Soft-delete masque l’accès texte
- Purge documentaire (`DocumentRetentionService`) supprime les blobs OCR
- Legal hold bloque la purge
- Tombstone : **pas** de texte OCR

## Consommateurs

RC2.5.4 Document Extraction lit exclusivement ces artefacts via `DocumentOCRService.open_text` (même version). Voir `docs/platform/document-extraction-architecture.md`.
