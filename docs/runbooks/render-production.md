# Runbook — Render production ELFIS Core

Référence opérationnelle. **Aucun secret dans ce fichier.**

`render.production.yaml` est une **référence / disaster recovery / future provisioning**.
**Ne pas** l’attacher ni le synchroniser avec le live Frankfurt sans revue préalable.

`render.yaml` = **investor-demo uniquement**. Ne pas le convertir en production.

## Architecture (5 ressources)

| Ressource | Type Render | Rôle |
|---|---|---|
| `elfis-core-api` | Web Service (Docker) | API HTTPS |
| `elfis-job-worker` | Background Worker (Docker) | `python -m app.jobs.job_worker` |
| `elfis-event-worker` | Background Worker (Docker) | `python -m app.events.event_worker` |
| `elfis-clamav` | Private Service (image) | `docker.io/clamav/clamav:1.5.4` · TCP 3310 |
| `elfis-core-db` | PostgreSQL **existant** | PG16 · ne pas recréer |

Région : **Frankfurt (EU Central)**.

Repo : `Junior0302/ELFIS` · branche `main` · root API/workers : `backend` · Dockerfile : `./Dockerfile`.

## Plans live (dashboard)

| Service | Plan ID live | Coût observé |
|---|---|---|
| API + 2 workers | `0.5c-512mb` | $7 / mois chacun |
| ClamAV | `2c-4g` | $85 / mois |
| Postgres | Basic-256mb / `0.1c-256mb` · 15 GB | **hors YAML** |

Instances : 1 partout. Auto Deploy : **OFF**.

## Stockage

- API : **aucun disque** persistant.
- Objets : Supabase privé `elfis-documents` + `elfis-vault`.
- `STORAGE_PROVIDER=supabase`.

## Antivirus

- ClamAV **privé**, pas dans l’image API.
- `CLAMD_HOST=elfis-clamav` · `CLAMD_PORT=3310`.
- Fail-closed. Uploads refusés si clamd injoignable.

## Base de données

- Nom live : `elfis-core-db`. Accès externe bloqué. Pooling désactivé.
- `DATABASE_URL` uniquement dans le dashboard (`sync: false` dans le template).
- Migrations : `python -m scripts.rc1.migrate_sql` (pre-deploy API).

## Health

- Check Render API : `GET /api/health/ready` → 200.

## IA / OCR

Actuellement **désactivés** (`ELFIS_AI_ENABLED`, OCR, auto extraction, `DOCUMENT_EXTRACTION_ENABLED`).

Workers : flags in-process `ELFIS_JOB_WORKER_ENABLED=false` et `ELFIS_EVENT_WORKER_ENABLED=false` (le process **est** le worker ; il ne doit pas en relancer un dans l’API).

## Secrets

Jamais dans Git. Dashboard uniquement. Ne jamais utiliser `generateValue` pour `JWT_SECRET` live.

## Déploiement manuel

1. Dashboard → service → **Manual Deploy** (commit voulu, ex. `2876a76` à la date de cette recette).
2. API : attendre pre-deploy `migrate_sql` puis health `/api/health/ready` = 200.
3. Vérifier logs workers : `job_worker_start` / event worker start.
4. Ne pas toucher Postgres, Stripe, Bridge, Brevo, Firebase, Supabase depuis un sync blueprint.

## Interdits

- Sync `render.production.yaml` → live sans revue.
- Recréer `elfis-core-db`.
- Remettre un disque `/data` sur l’API.
- Installer ClamAV dans l’image API.
- Réactiver le blueprint investor-demo (`render.yaml`) sur la prod.
