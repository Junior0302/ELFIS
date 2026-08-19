# Validation staging — Storage RC2.4 étape 3

## Script

```bash
cd backend
python -m scripts.rc2.validate_storage_stage3_staging --apply-sql
python -m scripts.rc2.validate_storage_stage3_staging --db-only
python -m scripts.rc2.validate_storage_stage3_staging --local-root /tmp/elfis-st3
```

## Séparation DB / provider

La DB staging peut être PostgreSQL tandis que le provider local utilise un répertoire temporaire.  
Les probes ne touchent **jamais** de documents utilisateurs réels.

## Probes

1. Tables stage3 présentes
2. Création document + version 1
3. Version 2
4. Archive / unarchive
5. Soft-delete / restore
6. Legal hold bloque purge
7. Release + purge du probe uniquement
8. Tombstone

Statut attendu : `PASS` (JSON stdout).
