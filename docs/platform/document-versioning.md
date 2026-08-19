# Versioning documentaire — RC2.4 étape 3

## Modèle

`ElfisDocumentVersion` (`elfis_document_versions`) : versions immuables liées à un `ElfisStorageObject`.

`ElfisDocumentRecord.current_version_id` pointe vers la version courante.  
`current_storage_object_id` est conservé pour compatibilité (égal à l’objet de la version courante).

## Immutabilité

Une fois créée, une version ne modifie pas : `storage_object_id`, checksum, taille, MIME, `version_number`, `document_id`.  
Seuls évoluent : `status`, `superseded_at`, `archived_at`, `deleted_at`.

Contrôle **service** (`DocumentVersionService.assert_version_immutable`).  
Ce n’est **pas** une immutabilité cryptographique : un admin DB peut toujours altérer les lignes.

## Cycle

1. Upload document → version 1 (`current`)
2. Nouvelle version → ancienne `superseded`, nouvelle `current`
3. Document archivé → **pas** de nouvelle version
4. Soft-delete → pas de nouvelle version ; téléchargement refusé

## Restauration de version (stratégie B)

`POST .../versions/{version_id}/restore` crée une **nouvelle** version qui réutilise le même `storage_object_id` historique (pas de copie physique).  
La purge vérifie les références partagées avant suppression physique.

## Concurrence

- `SELECT … FOR UPDATE` sur le document (PostgreSQL)
- contrainte `UNIQUE(document_id, version_number)`
- retry limité (5) ; compensation fichier uniquement si nouvel objet non partagé

## Backfill

```bash
python -m scripts.storage.backfill_document_versions --preview
python -m scripts.storage.backfill_document_versions --execute --confirm --batch-size 500
```

Idempotent, aucune copie physique, hors uploads ComptaPilot.
