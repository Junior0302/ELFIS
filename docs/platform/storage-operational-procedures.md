# Procédures opérationnelles Storage

## Upload streaming

- Chunks : `STORAGE_UPLOAD_CHUNK_SIZE_BYTES` (défaut 64 KiB)
- Limite appliquée **pendant** la lecture (pas seulement Content-Length)
- Temporaires : namespace `_temp` — jamais exposés comme documents disponibles

## Compensation

Si la DB échoue après promotion physique :

1. Tentative de suppression du nouvel objet
2. Audit `STORAGE_OBJECT_COMPENSATED`
3. Sinon `STORAGE_OBJECT_ORPHAN_DETECTED` (préfixe de clé uniquement)

Ne jamais supprimer un objet préexistant partagé.

## Nettoyage temporaires

```bash
python -m scripts.storage.cleanup_temp --preview
python -m scripts.storage.cleanup_temp --execute --older-than-hours 24 --confirm
```

Preview par défaut ; confirmation obligatoire ; batch limité ; uniquement `_temp`.

## Orphelins

```bash
python -m scripts.storage.find_orphans --preview
```

Aucune suppression automatique.

## Versions / rétention / purge (étape 3)

```bash
python -m scripts.storage.backfill_document_versions --preview
python -m scripts.storage.backfill_document_versions --execute --confirm --batch-size 500

python -m scripts.storage.retention --preview
python -m scripts.storage.retention --purge --before YYYY-MM-DD --batch-size 100 --confirm
```

Production : `--confirm-production` obligatoire pour la purge.  
Legal hold et liens métier bloquants sont re-vérifiés juste avant suppression physique.

Voir [document-retention-policy.md](../security/document-retention-policy.md).

## Health

Seuils : `STORAGE_DISK_DEGRADED_PERCENT`, `STORAGE_DISK_UNHEALTHY_PERCENT`, `STORAGE_PROBE_TIMEOUT_SECONDS`.

Aucun chemin local dans les métriques frontend.
