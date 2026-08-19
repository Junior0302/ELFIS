# Rapport RC1 — Staging readiness technique

Date : 2026-07-21  
Release : ELFIS CORE v1.0.0 — RC1  
Étape : RC1.1 (socle PostgreSQL)

## Statut staging

**NOT EXECUTED** — aucun environnement staging déployé / aucune URL staging fournie dans cette session.

## Checklist staging technique (exécutable)

### Socle
- [ ] API déployée sur domaine staging
- [ ] Frontend staging
- [ ] PostgreSQL dédié (`…_staging` / `…_recette` / `…_rc1`)
- [ ] Workers job + event (processus séparés)
- [ ] Backup staging avant reset

### Providers (jamais live)
- [ ] `ELFIS_USE_MOCK_STRIPE=true` **ou** Stripe **test** uniquement
- [ ] Mailer sandbox / mock
- [ ] AI mock ou clé staging budget limité
- [ ] OCR désactivé
- [ ] Storage mock ou bucket staging isolé
- [ ] `ELFIS_DISABLE_EXTERNAL_NETWORK=true` pour campagne auto

### Sécurité / config
- [ ] `ELFIS_ENVIRONMENT=staging`
- [ ] CORS origines staging explicites
- [ ] JWT staging distinct
- [ ] OpenAPI acceptable
- [ ] Pas de comptes client réels
- [ ] Logs sans secrets

### Santé
- [ ] `/api/health/live`
- [ ] `/api/health/ready`
- [ ] Métriques accessibles (auth)
- [ ] Smoke :
  ```bash
  python scripts/production/smoke_test.py \
    --environment staging \
    --allow-staging \
    --base-url https://staging.example.com
  ```

### Données
- [ ] Seed synthétique uniquement
- [ ] Reset uniquement si `ELFIS_ALLOW_DATABASE_RESET=true` + nom allowlist

## Dépendances RC1.1

Le staging technique ne peut être déclaré **READY** qu’après :

1. Exécution live `run_postgres_validation.py` → PASS
2. Aucun BLOCKER RC1-PG-*
3. Smoke staging health PASS

Statut actuel : **NOT READY** (bloqué sur PostgreSQL live).

Aucun commit. Aucun push.
