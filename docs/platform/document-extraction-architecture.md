# Architecture — Document Extraction (RC2.5.4)

## Séparation

| Couche | Rôle |
|--------|------|
| OCR | Texte brut (artefact privé) |
| Extraction | Champs structurés validés contre un schéma |
| Validation métier / mapping comptable | Hors scope |

## Pipeline `document_extraction_v1`

1. validate_document_available  
2. resolve_effective_document_type  
3. select_extraction_schema  
4. select_extraction_source  
5. load_extraction_source  
6. perform_structured_extraction  
7. validate_extraction_schema  
8. persist_extraction_artifact  
9. finalize_extraction_result  
10. finalize_processing  

## Transport inter-steps

**Décision :** artefacts `StorageObject` draft (`extraction_source_draft_v1`, `extraction_provider_draft_v1`) référencés par ID dans `job.metadata_json`.  
Pas de cache process-local comme unique transport — un autre worker peut reprendre après expiration de lease.

## Source texte

Uniquement via `DocumentOCRService.open_text` (OCRAccessPolicy) pour la **même** `document_version_id`.  
Jamais lecture directe du fichier original par le provider rules.

## Défauts

- `DOCUMENT_EXTRACTION_ENABLED=false`
- `DOCUMENT_EXTRACTION_PROVIDER=noop`
- `DOCUMENT_EXTRACTION_AUTO_CONFIRM=false`
- Aucune IA / ComptaPilot
