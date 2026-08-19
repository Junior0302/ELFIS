# Production readiness — ELFIS Core

## Checklist

1. `ELFIS_ENVIRONMENT=production` / `APP_ENV=production`
2. `JWT_SECRET` ≥ 32 caractères, non défaut
3. `CORS_ORIGINS` listés (jamais `*`)
4. PostgreSQL (SQLite interdit)
5. `ELFIS_HSTS_ENABLED=true` derrière HTTPS
6. Stripe secrets si Billing actif
7. Vault Supabase configuré
8. `PLATFORM_ADMIN_EMAILS` défini
9. Appliquer SQL : `backend/sql/elfis_security_observability_postgres.sql` (+ modules existants)
10. Workers jobs/events en processus séparés
11. `ELFIS_JWT_ENFORCE_ISSUER_AUDIENCE` seulement après rotation tokens

## Validation startup

`assert_startup_configuration()` refuse le démarrage sur issues **fatal** en production.

## Endpoints ops

- `/api/health/live` `/api/health/ready`
- `/api/platform/security/*` `/api/platform/observability/*` `/api/platform/reliability/*`
