# Migration progressive de provider — RC2.4 étape 4

## CLI

```bash
python -m scripts.storage.migrate_provider --preview
python -m scripts.storage.migrate_provider \
  --from-provider local --to-provider supabase \
  --batch-size 50 --confirm --verify-checksum
```

Défauts : preview, keep-source, verify-checksum.  
`--delete-source-after-verify` optionnel.

## Table `elfis_storage_migrations`

Statuts : pending → copying → copied → verified → switched | failed | rolled_back

## Fallback lecture

Autorisé uniquement si migration `copied`/`verified` et cible absente — journalisé.  
Pas de fallback silencieux permanent.

## Intégrité

```bash
python -m scripts.storage.verify_integrity --preview
python -m scripts.storage.verify_integrity --full-checksum --confirm
```
