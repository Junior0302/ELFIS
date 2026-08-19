# Sécurité — Document Extraction (RC2.5.4)

## Interdits

Pas de valeurs extraites / texte OCR / montants / IBAN / TVA dans : logs, audit, listes API, résumés de job, métriques.

## IAM

Séparer metadata (`extractions.read`), contenu (`extractions.content.read`), revue, correction, providers/schemas manage.  
Platform admin **sans** `content.read` ne lit pas le JSON client.

## Artefacts

Namespace `processing-artifacts`, checksum, taille bornée, object_key jamais exposé.  
`/content` : nosniff + `Cache-Control: private, no-store`.

## Lifecycle

Quarantaine → blocked. Soft-delete → contenu inaccessible / correction bloquée.  
Purge : artefacts extraction **puis** OCR puis storage. Legal hold bloque. Tombstone sans valeurs.
