# Validation staging — Storage RC2.4 étape 4

```bash
cd backend
python -m scripts.rc2.validate_storage_stage4_staging --apply-sql
python -m scripts.rc2.validate_storage_stage4_staging --db-only
python -m scripts.rc2.validate_storage_stage4_staging --provider-only
```

Si `STORAGE_PROVIDER=supabase` et credentials staging : probe upload/download/health.  
Aucun secret dans la sortie JSON. Aucun document utilisateur réel.
