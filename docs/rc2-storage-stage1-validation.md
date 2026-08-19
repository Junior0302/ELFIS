# RC2.4 étape 1 — Validation Storage & Document Registry

## Livrables

- Module `backend/app/storage/`
- Tables SQL `elfis_storage_*` / `elfis_document_*`
- API `/api/document-registry`
- Permissions IAM + audit events
- `StorageHealthProvider` (activable, défaut mock)
- Tests `backend/tests/storage/`
- Docs platform + security

## Non-objectifs (respectés)

- Pas de migration complète des uploads existants
- Pas d’OCR / IA
- Pas d’UI bibliothèque documentaire
- Pas de provider distant forcé
- Pas de commit / push automatiques

## Commandes de validation

```bash
cd backend
python -m pytest tests/storage -q --tb=line
python -m pytest tests/audit -q --tb=line
python -m pytest tests/iam -q --tb=line
python -m pytest tests/system_health -q --tb=line
python -m pytest tests/platform_admin -q --tb=line
python -c "from app.main import app; print('routes', len(app.routes))"
```

Frontend :

```bash
cd frontend && npm run build
```

Staging PostgreSQL :

```bash
python scripts/rc2/validate_storage_stage1_staging.py --apply-sql
# ou validation DB seule si pas de disque local persistant adapté
python scripts/rc2/validate_storage_stage1_staging.py --db-only
```

## Staging notes

- Appliquer `sql/elfis_storage_documents_postgres.sql`
- Si le filesystem staging n’est pas adapté : valider les tables/index en DB, et le provider local dans un répertoire temporaire documenté (`STORAGE_LOCAL_ROOT`)
- Nettoyer les probes après contrôle health

## Critères PASS

- Tests storage verts
- Non-régression audit / IAM / health / platform_admin
- Routes FastAPI incrémentées
- Frontend build OK
- Aucune fuite de chemin / contenu dans API ou audit
