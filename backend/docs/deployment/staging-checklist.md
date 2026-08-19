# Checklist — Staging ELFIS Core

Légende : `[ ]` à faire · `[x]` fait

## Configuration
- [ ] `ELFIS_ENVIRONMENT=staging` (ou `APP_ENV=staging`)
- [ ] PostgreSQL dédié staging (nom contient staging/test/recette)
- [ ] Secrets staging distincts de la production
- [ ] Providers : Stripe **test**, AI clé staging, mailer domaine recette
- [ ] CORS = origines staging explicites (pas `*`)
- [ ] JWT secret ≥ 32 caractères (non défaut)
- [ ] OpenAPI : acceptable en staging
- [ ] Comptes recette autorisés **uniquement** via seed fonctionnel contrôlé

## Validation
- [ ] `python scripts/production/validate_production_config.py` (fatals attendus si env≠prod OK)
- [ ] `python scripts/production/check_secrets.py`
- [ ] `python scripts/production/check_migrations.py`
- [ ] SQL `backend/sql/*.sql` appliqués
- [ ] Index Phase F appliqués

## Runtime
- [ ] API démarre
- [ ] Workers démarrent (processus séparés recommandés)
- [ ] `/api/health/live` OK
- [ ] `/api/health/ready` OK
- [ ] Smoke : `python scripts/production/smoke_test.py --base-url https://staging…`
- [ ] Arrêt gracieux SIGTERM testé

## Go staging → prod
- [ ] Rapport Phase G PASS / risques documentés
- [ ] Backup staging testé
- [ ] Décision RPO/RTO documentée
