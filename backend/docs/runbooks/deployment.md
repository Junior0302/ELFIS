# Runbook — Déploiement ELFIS Core

## Objectif
Déployer une version taguée de l’API et des workers de façon reproductible, avec migrations SQL et smoke tests.

## Prérequis
- Accès secrets staging/production (coffre)
- Accès base PostgreSQL cible
- Tag/branch validé
- Backup base récent vérifié (`verify_backup.py`)
- Checklist staging ou production cochée

## Variantes hébergeur
Adapter les commandes `deploy` / `restart` à Railway, Render, Fly, Kubernetes, VM systemd, etc. Les étapes métier restent identiques.

## Procédure

1. **Vérifier branche/tag**
   ```bash
   git fetch --tags
   git checkout <tag>
   git rev-parse HEAD
   ```

2. **Vérifier secrets** (coffre, pas le dépôt)
   ```bash
   cd backend
   ELFIS_ENVIRONMENT=production python scripts/production/validate_production_config.py
   ```
   Attendu : `"ok": true` sans fatal.

3. **Sauvegarder la base** — voir `database-backup.md`. Noter le chemin et checksum.

4. **Migrations SQL** (Alembic absent V1)
   - Appliquer dans l’ordre documenté les scripts `backend/sql/*.sql` manquants (idempotents `IF NOT EXISTS`)
   - Puis `backend/docs/performance/postgres_indexes_phase_f.sql`
   ```bash
   python scripts/production/check_migrations.py
   ```

5. **Vérifier migrations** — tables critiques : `users`, `organizations`, `elfis_jobs`, `elfis_events`, vault, billing, search.

6. **Déployer l’API** — image/artefact du tag ; variables d’env production ; **workers in-process désactivés** (prod).

7. **Déployer les workers** (processus séparés)
   ```bash
   python -m app.jobs.job_worker
   python -m app.events.event_worker
   ```
   (ou entrypoints équivalents du packaging)

8. **Smoke tests**
   - Staging : `python scripts/production/smoke_test.py --base-url https://staging…`
   - Prod : `… --allow-production-readonly`

9. **Health**
   - `GET /api/health/live` → 200
   - `GET /api/health/ready` → 200 (`ok` ou `degraded` si provider optionnel)

10. **Métriques / erreurs** — surveiller 5xx, jobs failed, events failed 15–30 min.

11. **Confirmer ou rollback** — voir `rollback.md`.

## Contrôles
| Contrôle | Attendu |
|----------|---------|
| validate_production_config | ok |
| ready | status ok/degraded |
| workers logs | job_worker_start / event_worker_start |
| aucun mock provider | flags production |

## Rollback
Voir `rollback.md`. Ne pas downgrader SQL destructif sans plan.

## Escalade
Incident critique → platform admin + runbook incident concerné (Stripe / worker / storage / AI).

## Ne jamais
- Déployer avec `ELFIS_ENVIRONMENT=production` et SQLite
- Activer mocks en production
- Seed fonctionnel sur prod
- Pousser `.env` dans git
