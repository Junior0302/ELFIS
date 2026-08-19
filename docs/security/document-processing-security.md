# Sécurité — Document Processing

## Règles

- Isolation multi-tenant stricte (org sur job = org document)
- Pas de contenu documentaire en logs / audit / summaries
- Pas de secrets, clés API, chemins physiques, URLs signées
- Messages d’erreur sanitisés (longueur bornée)
- Handlers ne mute pas les statuts DB (orchestrateur seul)
- Retry borné (`max_attempts`, codes retryables)

## Quarantaine / purge

- Objet quarantined → job `blocked` (pipeline normal)
- Document purgé → échec non retryable / création refusée
- Soft-delete → blocked

## OCR (RC2.5.3)

- Texte OCR = contenu sensible (pas logs / audit / listes)
- Quarantaine : aucun open provider
- Accès texte : `document_processing.ocr.text.read` uniquement
- Purge documentaire : suppression des artefacts OCR (legal hold bloque)

## Extraction (RC2.5.4)

- Valeurs structurées = sensibles (pas audit / listes)
- Source via OCRAccessPolicy uniquement
- Accès contenu : `document_processing.extractions.content.read`
- Purge : artefacts extraction avant OCR

## Scaling futur

Workers horizontaux via claim SKIP LOCKED ; pas de broker Redis requis pour RC2.5.1.
